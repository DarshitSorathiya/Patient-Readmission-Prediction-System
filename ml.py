# ============================================================================================================================
# PROJECT      : Diabetes 130-US Hospitals (1999–2008) — Complete ML Pipeline
# FILE         : diabetes_ml_pipeline.py
# VERSION      : 2.0  (Added: SMOTE upsampling + Random Forest + Model Comparison)
# DESCRIPTION  : End-to-end ML pipeline connecting to PostgreSQL gold tables.
#
#                Stage 1 → Export data from PostgreSQL
#                Stage 2 → Prepare features  (NULL imputation for Random Forest)
#                Stage 3 → SMOTE upsampling  (training data ONLY — never val/test)
#                Stage 4 → Train Random Forest  (on SMOTE-resampled data)
#                Stage 5 → Train XGBoost        (on SMOTE-resampled data)
#                Stage 6 → Evaluate & Compare   (AUC, F1, Recall, Precision + plots)
#                Stage 7 → Write best model predictions back to PostgreSQL
#
# WHY SMOTE:
#   After deduplication the dataset has ~5% positive class (readmitted=1).
#   SMOTE creates synthetic positive samples by interpolating between real
#   minority class neighbors in feature space.
#   Result: balanced training set → both models learn the positive class properly.
#   CRITICAL: SMOTE applied ONLY to training data. Val and test stay untouched.
#             Applying SMOTE to val/test is data leakage — metrics would be wrong.
#
# PREREQUISITES:
#   pip install psycopg2-binary sqlalchemy pandas scikit-learn xgboost
#               imbalanced-learn matplotlib seaborn shap joblib
#
# HOW TO RUN:
#   python diabetes_ml_pipeline.py
#   Or cell by cell in Jupyter / VS Code
# ============================================================================================================================


# ── Imports ───────────────────────────────────────────────────────────────────
import os
import warnings
import joblib
import numpy  as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sqlalchemy import create_engine, text

# Sklearn
from sklearn.ensemble    import RandomForestClassifier
from sklearn.metrics     import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay,
    RocCurveDisplay, roc_auc_score, precision_score, recall_score, f1_score,
    fbeta_score,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.impute          import SimpleImputer

# XGBoost
from xgboost import XGBClassifier

# SMOTE
try:
    from imblearn.over_sampling import SMOTE
    from imblearn.over_sampling import BorderlineSMOTE
    from imblearn.combine import SMOTEENN
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    print("WARNING: imbalanced-learn not installed. Run: pip install imbalanced-learn")

# SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("WARNING: SHAP not installed. Run: pip install shap")

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-whitegrid')


# ============================================================================================================================
# CONFIGURATION — Edit only this block before running
# ============================================================================================================================

DB_CONFIG = {
    "host"    : "localhost",
    "port"    : 5433,
    "database": "diabetes_pipeline",
    "user"    : "postgres",
    "password": "darshit89",        # <- Replace with your actual password
}

# Columns that are NOT model features
NON_FEATURE_COLS = [
    'encounter_id',
    'patient_nbr',
    'data_split',
    'readmitted',           # target variable — never a feature
    'class_weight',         # metadata only
    'stratification_key',   # metadata only
]

# SMOTE settings
SMOTE_STRATEGY    = 1.0    # after SMOTE: minority = 100% of majority count
SMOTE_K_NEIGHBORS = 5      # nearest neighbors used to synthesize new samples

# Alternative imbalance strategies to compare
BORDERLINE_SMOTE_KIND = 'borderline-1'
USE_SMOTEENN = True

# Threshold tuning settings (to improve recall/F1 in imbalanced scenarios)
THRESHOLD_MIN      = 0.10
THRESHOLD_MAX      = 0.90
THRESHOLD_STEPS    = 161
THRESHOLD_F_BETA   = 2.0   # beta>1 emphasizes recall more than precision
THRESHOLD_MIN_PREC = 0.10  # avoid thresholds that flood positives too much
THRESHOLD_MAX_PRED_POS_RATE = 0.40

# Output directory for saved models and plots
OUTPUT_DIR  = "./diabetes_ml_outputs"
RANDOM_SEED = 42
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================================================================
# STAGE 1 — Load Data from PostgreSQL
# ============================================================================================================================

def get_engine():
    """Create SQLAlchemy engine connected to diabetes_pipeline database."""
    url = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(url, echo=False)


def load_data(engine):
    """Load train / validation / test splits from gold.ml_dataset."""
    print("\n" + "="*70)
    print("STAGE 1 — Loading data from PostgreSQL gold.ml_dataset")
    print("="*70)

    df_train = pd.read_sql(
        "SELECT * FROM gold.ml_dataset WHERE data_split = 'train'", engine)
    df_val   = pd.read_sql(
        "SELECT * FROM gold.ml_dataset WHERE data_split = 'validation'", engine)
    df_test  = pd.read_sql(
        "SELECT * FROM gold.ml_dataset WHERE data_split = 'test'", engine)

    print(f"\n  Train rows      : {len(df_train):,}")
    print(f"  Validation rows : {len(df_val):,}")
    print(f"  Test rows       : {len(df_test):,}")
    print(f"  Total columns   : {df_train.shape[1]}")

    print(f"\n  Class distribution BEFORE resampling (train):")
    vc = df_train['readmitted'].value_counts()
    for cls, cnt in vc.items():
        label = "Readmitted <30 (Positive)" if cls == 1 else "Not Readmitted  (Negative)"
        print(f"    {label} : {cnt:,}  ({cnt/len(df_train)*100:.2f}%)")

    ratio = vc[0] / vc.get(1, 1)
    print(f"\n  Imbalance ratio : {ratio:.1f}:1  (negative:positive)")
    print(f"  -> SMOTE will create synthetic positive samples to fix this")

    return df_train, df_val, df_test


# ============================================================================================================================
# STAGE 2 — Prepare Features
# ============================================================================================================================

def prepare_features(df_train, df_val, df_test):
    """
    Separate X / y / weights / IDs.
    Imputes NULLs using training median — Random Forest cannot handle NULLs natively.
    XGBoost handles NULLs internally but imputed data works for both.
    """
    print("\n" + "="*70)
    print("STAGE 2 — Preparing features")
    print("="*70)

    def split_df(df):
        X   = df.drop(columns=NON_FEATURE_COLS, errors='ignore')
        y   = df['readmitted'].astype(int)
        w   = df['class_weight']
        ids = df['encounter_id']
        return X, y, w, ids

    X_train, y_train, w_train, ids_train = split_df(df_train)
    X_val,   y_val,   w_val,   ids_val   = split_df(df_val)
    X_test,  y_test,  w_test,  ids_test  = split_df(df_test)

    print(f"\n  Feature columns : {X_train.shape[1]}")

    # NULL imputation — fit on training only, transform val and test
    null_cols = X_train.columns[X_train.isnull().any()].tolist()
    if null_cols:
        print(f"\n  {len(null_cols)} columns with NULLs — imputing with training median:")
        for col in null_cols:
            print(f"    {col}")
        imputer = SimpleImputer(strategy='median')
        X_train = pd.DataFrame(
            imputer.fit_transform(X_train), columns=X_train.columns)
        X_val   = pd.DataFrame(
            imputer.transform(X_val),       columns=X_val.columns)
        X_test  = pd.DataFrame(
            imputer.transform(X_test),      columns=X_test.columns)
        joblib.dump(imputer, os.path.join(OUTPUT_DIR, "median_imputer.pkl"))
        print(f"  Imputer saved to {OUTPUT_DIR}/median_imputer.pkl")
    else:
        print(f"\n  No NULLs found — imputation not needed")
        imputer = None

    # Class imbalance ratio
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = round(neg / pos, 4)
    print(f"\n  scale_pos_weight (neg/pos) : {scale_pos_weight}")
    print(f"  -> Used by XGBoost to weight the minority class")

    return (X_train, y_train, w_train, ids_train,
            X_val,   y_val,   w_val,   ids_val,
            X_test,  y_test,  w_test,  ids_test,
            scale_pos_weight, imputer)


# ============================================================================================================================
# STAGE 3 — SMOTE Upsampling
# Applied to TRAINING DATA ONLY. Val and test are never touched.
# ============================================================================================================================

def apply_smote(X_train, y_train):
    """
    SMOTE — Synthetic Minority Oversampling Technique.

    How it works:
      For each minority class sample (readmitted=1):
        1. Find its k nearest neighbors in feature space (also minority class)
        2. Pick one neighbor randomly
        3. Create a new synthetic sample on the line between original and neighbor:
               new_sample = original + random(0,1) x (neighbor - original)
        4. Repeat until the desired ratio is reached

    Why NOT apply to val/test:
      Val and test simulate real deployment. Real patients are not synthetic.
      Metrics computed on resampled val/test would be artificially inflated
      and would not reflect real-world performance.

    SMOTE_STRATEGY = 0.5:
      minority becomes 50% of majority after resampling.
      Example: 38000 negative, 2000 positive
        -> SMOTE adds 17000 synthetic positives
        -> Result: 38000 negative, 19000 positive
    """
    if not SMOTE_AVAILABLE:
        print("\n  SMOTE not available — training on original imbalanced data")
        return X_train, y_train

    print("\n" + "="*70)
    print("STAGE 3 — SMOTE Upsampling  (training data ONLY)")
    print("="*70)

    before_neg = (y_train == 0).sum()
    before_pos = (y_train == 1).sum()

    print(f"\n  Before SMOTE:")
    print(f"    Negative : {before_neg:,}")
    print(f"    Positive : {before_pos:,}")
    print(f"    Ratio    : {before_neg/before_pos:.1f}:1")

    smote = SMOTE(
        sampling_strategy = SMOTE_STRATEGY,
        k_neighbors       = SMOTE_K_NEIGHBORS,
        random_state      = RANDOM_SEED,
        n_jobs            = -1,
    )
    X_res, y_res = smote.fit_resample(X_train, y_train)

    after_neg  = (y_res == 0).sum()
    after_pos  = (y_res == 1).sum()
    synthetic  = after_pos - before_pos

    print(f"\n  After SMOTE:")
    print(f"    Negative  : {after_neg:,}   (unchanged — all real rows)")
    print(f"    Positive  : {after_pos:,}   (+{synthetic:,} synthetic samples created)")
    print(f"    New ratio : {after_neg/after_pos:.1f}:1")
    print(f"    Total     : {len(X_res):,} rows (was {len(X_train):,})")
    print(f"\n  Val and Test sets are UNCHANGED")
    print(f"  Synthetic rows exist only in training — never in evaluation")

    return pd.DataFrame(X_res, columns=X_train.columns), pd.Series(y_res)


def build_resampling_variants(X_train, y_train):
    """
    Create multiple train-set variants for fair imbalance strategy comparison.

    Strategies:
      - Original (no-resampling)
      - SMOTE
      - BorderlineSMOTE
      - SMOTEENN (optional)
    """
    print("\n" + "="*70)
    print("STAGE 3B — Building imbalance strategy variants")
    print("="*70)

    variants = {
        'Original': (X_train.copy(), y_train.copy())
    }

    neg = int((y_train == 0).sum())
    pos = int((y_train == 1).sum())
    print(f"\n  Base train distribution: neg={neg:,}, pos={pos:,}, ratio={neg/max(pos,1):.1f}:1")

    if not SMOTE_AVAILABLE:
        print("  imbalanced-learn unavailable -> only Original strategy will be used")
        return variants

    # SMOTE
    sm = SMOTE(
        sampling_strategy=SMOTE_STRATEGY,
        k_neighbors=SMOTE_K_NEIGHBORS,
        random_state=RANDOM_SEED,
    )
    X_sm, y_sm = sm.fit_resample(X_train, y_train)
    variants['SMOTE'] = (pd.DataFrame(X_sm, columns=X_train.columns), pd.Series(y_sm))

    # BorderlineSMOTE
    bsm = BorderlineSMOTE(
        sampling_strategy=SMOTE_STRATEGY,
        k_neighbors=SMOTE_K_NEIGHBORS,
        kind=BORDERLINE_SMOTE_KIND,
        random_state=RANDOM_SEED,
    )
    X_bsm, y_bsm = bsm.fit_resample(X_train, y_train)
    variants['BorderlineSMOTE'] = (pd.DataFrame(X_bsm, columns=X_train.columns), pd.Series(y_bsm))

    # SMOTEENN often improves class boundary cleaning after synthetic generation.
    if USE_SMOTEENN:
        sme = SMOTEENN(
            sampling_strategy=SMOTE_STRATEGY,
            random_state=RANDOM_SEED,
        )
        X_sme, y_sme = sme.fit_resample(X_train, y_train)
        variants['SMOTEENN'] = (pd.DataFrame(X_sme, columns=X_train.columns), pd.Series(y_sme))

    print("\n  Variant distributions:")
    for name, (_, vy) in variants.items():
        vneg = int((vy == 0).sum())
        vpos = int((vy == 1).sum())
        print(f"    {name:<15} neg={vneg:,} pos={vpos:,} ratio={vneg/max(vpos,1):.2f}:1")

    return variants


# ============================================================================================================================
# STAGE 4 — Train Random Forest
# ============================================================================================================================

def train_random_forest(X_train_smote, y_train_smote, X_val, y_val):
    """
    Train Random Forest on SMOTE-resampled training data.

    Random Forest builds N decision trees in parallel, each on a random
    bootstrap sample of rows and a random subset of features.
    Final prediction = majority vote across all trees.

    Strengths: robust to overfitting, handles mixed feature types well,
               gives reliable feature importance via Gini impurity.
    Limitation: slower than XGBoost, cannot handle NULLs natively.
    """
    print("\n" + "="*70)
    print("STAGE 4 — Training Random Forest  (on SMOTE data)")
    print("="*70)

    # Your code as requested — with enterprise parameters added
    rf_model = RandomForestClassifier(
        n_estimators      = 200,         # number of trees in the forest
        max_depth         = None,        # grow full trees — depth controlled by min_samples
        min_samples_split = 10,          # minimum samples to attempt a split
        min_samples_leaf  = 5,           # minimum samples at each leaf node
        max_features      = 'sqrt',      # sqrt(n_features) per tree — standard for classification
        class_weight      = 'balanced',  # adjusts weights inversely to class frequency
        random_state      = 42,
        n_jobs            = -1,
    )

    print(f"\n  Training on {len(X_train_smote):,} rows (after SMOTE)...")

    rf_model.fit(X_train_smote, y_train_smote)

    val_auc = roc_auc_score(y_val, rf_model.predict_proba(X_val)[:, 1])
    print(f"\n  Random Forest trained successfully")
    print(f"  Validation AUC : {val_auc:.4f}")

    path = os.path.join(OUTPUT_DIR, "random_forest_diabetes.pkl")
    joblib.dump(rf_model, path)
    print(f"  Model saved    : {path}")

    return rf_model


# ============================================================================================================================
# STAGE 5 — Train XGBoost
# ============================================================================================================================

def train_xgboost(train_variants, X_val, y_val, scale_pos_weight):
    """
    Train XGBoost on SMOTE-resampled training data.

    XGBoost builds trees sequentially — each tree corrects the residual errors
    of the previous ensemble. Uses gradient descent on a loss function.

    After SMOTE the data is ~balanced so scale_pos_weight is reduced from the
    original imbalance ratio down to 2.0 (slight positive emphasis for recall).
    """
    print("\n" + "="*70)
    print("STAGE 5 — Training XGBoost  (on SMOTE data)")
    print("="*70)

    variant_reports = []
    chosen_model = None
    chosen_name = None
    chosen_threshold = 0.5
    chosen_metrics = None
    best_val_f1 = -1

    print("\n  Training and comparing imbalance variants:")
    for variant_name, (X_train_var, y_train_var) in train_variants.items():
        use_full_weight = (variant_name == 'Original')
        spw = scale_pos_weight if use_full_weight else min(scale_pos_weight, 2.0)

        xgb_model = XGBClassifier(
            n_estimators          = 700 if use_full_weight else 500,
            max_depth             = 5 if use_full_weight else 6,
            min_child_weight      = 8 if use_full_weight else 5,
            gamma                 = 0.2 if use_full_weight else 0.1,
            subsample             = 0.85 if use_full_weight else 0.8,
            colsample_bytree      = 0.85 if use_full_weight else 0.8,
            colsample_bylevel     = 0.85 if use_full_weight else 0.8,
            learning_rate         = 0.04 if use_full_weight else 0.05,
            scale_pos_weight      = spw,
            reg_alpha             = 0.2 if use_full_weight else 0.1,
            reg_lambda            = 1.2 if use_full_weight else 1.0,
            eval_metric           = ['aucpr', 'auc', 'logloss'],
            early_stopping_rounds = 40 if use_full_weight else 30,
            random_state          = RANDOM_SEED,
            n_jobs                = -1,
            verbosity             = 0,
        )

        print(f"    -> {variant_name:<15} rows={len(X_train_var):,}, scale_pos_weight={spw:.3f}")
        xgb_model.fit(
            X_train_var, y_train_var,
            eval_set=[(X_train_var, y_train_var), (X_val, y_val)],
            verbose=0,
        )

        val_proba = xgb_model.predict_proba(X_val)[:, 1]
        t, _, m = _find_best_threshold(y_val, val_proba)
        val_auc = roc_auc_score(y_val, val_proba)
        val_ap = average_precision_score(y_val, val_proba)

        variant_reports.append(
            {
                'variant': variant_name,
                'threshold': t,
                'val_auc': val_auc,
                'val_ap': val_ap,
                'val_f1': m['f1'],
                'val_recall': m['recall'],
                'val_precision': m['precision'],
            }
        )

        if (m['f1'] > best_val_f1) or (m['f1'] == best_val_f1 and (chosen_metrics is None or m['recall'] > chosen_metrics['recall'])):
            best_val_f1 = m['f1']
            chosen_model = xgb_model
            chosen_name = variant_name
            chosen_threshold = t
            chosen_metrics = m

    print("\n  Variant comparison on validation set:")
    print(f"    {'Variant':<16} {'Thr':>6} {'F1':>8} {'Recall':>8} {'Prec':>8} {'PR-AUC':>8} {'ROC-AUC':>8}")
    print(f"    {'-'*70}")
    for r in variant_reports:
        print(
            f"    {r['variant']:<16} {r['threshold']:>6.3f} {r['val_f1']:>8.4f} "
            f"{r['val_recall']:>8.4f} {r['val_precision']:>8.4f} {r['val_ap']:>8.4f} {r['val_auc']:>8.4f}"
        )

    xgb_model = chosen_model

    print(f"\n  Chosen XGBoost variant: {chosen_name}")

    val_auc = roc_auc_score(y_val, xgb_model.predict_proba(X_val)[:, 1])
    val_ap  = average_precision_score(y_val, xgb_model.predict_proba(X_val)[:, 1])
    print(f"\n  XGBoost trained successfully")
    print(f"  Best iteration : {xgb_model.best_iteration}")
    print(f"  Validation AUC : {val_auc:.4f}")
    print(f"  Validation AP  : {val_ap:.4f}")
    print(f"  Suggested threshold from validation: {chosen_threshold:.3f}")
    print(f"  Suggested threshold metrics: F1={chosen_metrics['f1']:.4f}, Recall={chosen_metrics['recall']:.4f}, Precision={chosen_metrics['precision']:.4f}")

    xgb_model.save_model(os.path.join(OUTPUT_DIR, "xgboost_diabetes.json"))
    joblib.dump(xgb_model,  os.path.join(OUTPUT_DIR, "xgboost_diabetes.pkl"))
    print(f"  Model saved    : {OUTPUT_DIR}/xgboost_diabetes.json + .pkl")

    return xgb_model


# ============================================================================================================================
# STAGE 6 — Evaluate & Compare Both Models
# ============================================================================================================================

def _find_best_threshold(y_true, y_proba, beta=THRESHOLD_F_BETA):
    """
    Tune threshold on validation data only.
    Uses F-beta so recall can be emphasized for rare positive class.
    """
    thresholds = np.linspace(THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_STEPS)
    best_t = 0.5
    best_score = -1
    best_metrics = {'precision': 0.0, 'recall': 0.0, 'f1': 0.0, 'fbeta': 0.0, 'pred_pos_rate': 0.0}

    for t in thresholds:
        pred = (y_proba >= t).astype(int)
        precision = precision_score(y_true, pred, zero_division=0)
        recall = recall_score(y_true, pred, zero_division=0)
        f1 = f1_score(y_true, pred, zero_division=0)
        fbeta = fbeta_score(y_true, pred, beta=beta, zero_division=0)
        pred_pos_rate = pred.mean()

        # Guardrails: avoid unusable operating points with too many alerts.
        if precision < THRESHOLD_MIN_PREC:
            continue
        if pred_pos_rate > THRESHOLD_MAX_PRED_POS_RATE:
            continue

        score = (0.75 * f1) + (0.25 * recall)
        if score > best_score:
            best_score = score
            best_t = float(t)
            best_metrics = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'fbeta': fbeta,
                'pred_pos_rate': float(pred_pos_rate),
            }

    # Fallback if guardrails filtered every threshold
    if best_score < 0:
        for t in thresholds:
            pred = (y_proba >= t).astype(int)
            precision = precision_score(y_true, pred, zero_division=0)
            recall = recall_score(y_true, pred, zero_division=0)
            f1 = f1_score(y_true, pred, zero_division=0)
            fbeta = fbeta_score(y_true, pred, beta=beta, zero_division=0)
            score = (0.75 * f1) + (0.25 * recall)
            if score > best_score:
                best_score = score
                best_t = float(t)
                best_metrics = {
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                    'fbeta': fbeta,
                    'pred_pos_rate': float(pred.mean()),
                }

    return best_t, best_score, best_metrics


def evaluate_and_compare(rf_model, xgb_model,
                         X_val, y_val,
                         X_test, y_test,
                         feature_names):
    """
    Evaluate BOTH models on the TEST SET (original, no SMOTE).
    Produces side-by-side metrics + 4 comparison plots.
    """
    print("\n" + "="*70)
    print("STAGE 6 — Evaluate & Compare  Random Forest  vs  XGBoost")
    print("="*70)

    models  = {'Random Forest': rf_model, 'XGBoost': xgb_model}
    results = {}

    thresholds = {}

    for name, model in models.items():
        val_proba = model.predict_proba(X_val)[:, 1]
        best_t, best_score, best_m = _find_best_threshold(y_val, val_proba)
        thresholds[name] = best_t

        proba = model.predict_proba(X_test)[:, 1]
        pred  = (proba >= best_t).astype(int)
        results[name] = {
            'threshold': best_t,
            'val_score': best_score,
            'val_fbeta': best_m['fbeta'],
            'val_f1': best_m['f1'],
            'val_recall': best_m['recall'],
            'val_precision': best_m['precision'],
            'proba'    : proba,
            'pred'     : pred,
            'auc'      : roc_auc_score(y_test, proba),
            'ap'       : average_precision_score(y_test, proba),
            'precision': precision_score(y_test, pred, zero_division=0),
            'recall'   : recall_score(y_test,   pred, zero_division=0),
            'f1'       : f1_score(y_test,        pred, zero_division=0),
        }

    print(f"\n  Tuned thresholds (selected on validation set with F1/Recall objective):")
    for name in models:
        print(
            f"    {name:<14} threshold={results[name]['threshold']:.3f} "
            f"val_F1={results[name]['val_f1']:.4f} "
            f"val_Recall={results[name]['val_recall']:.4f} "
            f"val_Precision={results[name]['val_precision']:.4f}"
        )

    # Metrics comparison table
    print(f"\n  {'Metric':<26} {'Random Forest':>15} {'XGBoost':>15}  {'Winner':>14}")
    print(f"  {'-'*72}")

    metric_rows  = [
        ('ROC-AUC  (Test Set)', 'auc'),
        ('PR-AUC   (Test Set)', 'ap'),
        ('Precision',           'precision'),
        ('Recall  (Sensitivity)','recall'),
        ('F1 Score',            'f1'),
    ]
    winner_counts = {'Random Forest': 0, 'XGBoost': 0}

    for label, key in metric_rows:
        rf_v  = results['Random Forest'][key]
        xgb_v = results['XGBoost'][key]
        w     = 'Random Forest' if rf_v > xgb_v else 'XGBoost'
        winner_counts[w] += 1
        print(f"  {label:<26} {rf_v:>15.4f} {xgb_v:>15.4f}  {w:>14}")

    print(f"\n  Classification Report — Random Forest:")
    print(classification_report(y_test, results['Random Forest']['pred'],
          target_names=['Not Readmitted', 'Readmitted <30']))

    print(f"  Classification Report — XGBoost:")
    print(classification_report(y_test, results['XGBoost']['pred'],
          target_names=['Not Readmitted', 'Readmitted <30']))

    best_name  = max(winner_counts, key=winner_counts.get)
    best_model = models[best_name]
    print(f"  Best Overall Model : {best_name}  "
            f"(won {winner_counts[best_name]}/5 metrics)")
    print(f"  -> This model will be used for predictions in Stage 7")

    # Plots
    _plot_confusion_matrices(results, y_test)
    _plot_roc_curves(results, y_test)
    _plot_feature_importances(rf_model, xgb_model, feature_names)
    _plot_score_distributions(results, y_test, thresholds)
    _plot_learning_curves_xgb(xgb_model)

    if SHAP_AVAILABLE:
        print(f"\n  Computing SHAP values for XGBoost...")
        _plot_shap(xgb_model, X_test, feature_names)

    return results, best_name, best_model, thresholds[best_name]


def _plot_confusion_matrices(results, y_test):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    colors = {'Random Forest': 'Greens', 'XGBoost': 'Blues'}
    for ax, (name, res) in zip(axes, results.items()):
        cm = confusion_matrix(y_test, res['pred'])
        ConfusionMatrixDisplay(cm,
            display_labels=['Not Readmitted', 'Readmitted <30']
        ).plot(ax=ax, colorbar=False, cmap=colors[name])
        ax.set_title(
            f"{name}\nAUC={res['auc']:.4f}  |  F1={res['f1']:.4f}  |  Recall={res['recall']:.4f}",
            fontsize=11, fontweight='bold'
        )
    plt.suptitle('Confusion Matrices — RF vs XGBoost  (Test Set)',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "confusion_matrix_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n  Saved: {path}")


def _plot_roc_curves(results, y_test):
    fig, ax = plt.subplots(figsize=(8, 7))
    colors  = {'Random Forest': '#10B981', 'XGBoost': '#2563EB'}
    for name, res in results.items():
        RocCurveDisplay.from_predictions(
            y_test, res['proba'],
            name  = f"{name}  (AUC = {res['auc']:.4f})",
            ax    = ax,
            color = colors[name],
        )
    ax.plot([0, 1], [0, 1], 'k--', lw=1.5, label='Random Baseline (AUC=0.50)')
    ax.set_title('ROC Curve Comparison — Test Set', fontsize=14, fontweight='bold')
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate (Recall)', fontsize=12)
    ax.legend(fontsize=11, loc='lower right')
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "roc_curve_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")


def _plot_feature_importances(rf_model, xgb_model, feature_names):
    rf_imp  = pd.Series(rf_model.feature_importances_,
                        index=feature_names).sort_values(ascending=False).head(15)
    xgb_imp = pd.Series(xgb_model.feature_importances_,
                        index=feature_names).sort_values(ascending=False).head(15)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    rf_imp.sort_values().plot(
        kind='barh', ax=axes[0], color='#10B981')
    axes[0].set_title('Random Forest — Top 15 Features\n(Gini Impurity)',
                      fontsize=12, fontweight='bold')

    xgb_imp.sort_values().plot(
        kind='barh', ax=axes[1], color='#2563EB')
    axes[1].set_title('XGBoost — Top 15 Features\n(Gain)',
                      fontsize=12, fontweight='bold')

    # Highlight features that appear in both top 15 lists
    common = set(rf_imp.index[:10]) & set(xgb_imp.index[:10])
    if common:
        print(f"\n  Features in both top-10 lists (most stable predictors):")
        for f in sorted(common):
            print(f"    {f}")

    plt.suptitle('Feature Importance Comparison',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "feature_importance_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")


def _plot_score_distributions(results, y_test, thresholds):
    """
    Well-separated distributions = model discriminates between classes well.
    Red (positive class) should be shifted rightward vs blue (negative class).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, (name, res) in zip(axes, results.items()):
        ax.hist(res['proba'][y_test == 0], bins=40, alpha=0.6,
                color='#2563EB', label='Not Readmitted (0)', density=True)
        ax.hist(res['proba'][y_test == 1], bins=40, alpha=0.6,
                color='#EF4444', label='Readmitted <30 (1)',  density=True)
        t = thresholds.get(name, 0.5)
        ax.axvline(t, color='black', linestyle='--', lw=1.5,
               label=f'Threshold={t:.2f}')
        ax.set_title(f'{name}\nAUC={res["auc"]:.4f}',
                     fontsize=12, fontweight='bold')
        ax.set_xlabel('Predicted Probability (Readmission Risk)', fontsize=10)
        ax.set_ylabel('Density', fontsize=10)
        ax.legend(fontsize=9)
    plt.suptitle('Score Distribution — Well separated = good discrimination',
                 fontsize=12, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "score_distribution_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")


def _plot_learning_curves_xgb(xgb_model):
    """Train vs Validation AUC over boosting rounds for XGBoost."""
    res = xgb_model.evals_result()
    if not res:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(res['validation_0']['auc'],   label='Train AUC', color='#2563EB', lw=2)
    axes[0].plot(res['validation_1']['auc'],   label='Val AUC',   color='#F59E0B', lw=2, ls='--')
    axes[0].axvline(xgb_model.best_iteration, color='red', ls=':', lw=1.5,
                    label=f'Best ({xgb_model.best_iteration})')
    axes[0].set_title('XGBoost — AUC Over Rounds', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Round')
    axes[0].set_ylabel('AUC')
    axes[0].legend()

    axes[1].plot(res['validation_0']['logloss'], label='Train LogLoss', color='#2563EB', lw=2)
    axes[1].plot(res['validation_1']['logloss'], label='Val LogLoss',   color='#F59E0B', lw=2, ls='--')
    axes[1].axvline(xgb_model.best_iteration,   color='red', ls=':', lw=1.5,
                    label=f'Best ({xgb_model.best_iteration})')
    axes[1].set_title('XGBoost — LogLoss Over Rounds', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Round')
    axes[1].set_ylabel('Log Loss')
    axes[1].legend()

    plt.suptitle('XGBoost Learning Curves', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "xgboost_learning_curves.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")


def _plot_shap(model, X_test, feature_names):
    """SHAP explainability — shows which features drive each prediction."""
    sample_size = min(500, len(X_test))
    X_sample    = X_test.sample(sample_size, random_state=RANDOM_SEED)
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    shap.summary_plot(shap_values, X_sample, plot_type='bar',
                      max_display=20, show=False)
    plt.title('SHAP — Mean Feature Importance (XGBoost)',
              fontsize=13, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "shap_importance_xgboost.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")

    shap.summary_plot(shap_values, X_sample, max_display=20, show=False)
    plt.title('SHAP Beeswarm — Feature Impact Direction (XGBoost)',
              fontsize=13, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "shap_beeswarm_xgboost.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"  Saved: {path}")


# ============================================================================================================================
# BONUS — Cross-Validation on SMOTE training data
# ============================================================================================================================

def cross_validate_both(X_train_smote, y_train_smote, scale_pos_weight, n_folds=5):
    """Stratified k-fold CV for both models on SMOTE training data."""
    print("\n" + "="*70)
    print(f"BONUS — {n_folds}-Fold Stratified Cross-Validation (SMOTE training data)")
    print("="*70)

    cv_models = {
        'Random Forest': RandomForestClassifier(
            n_estimators=100, class_weight='balanced',
            random_state=RANDOM_SEED, n_jobs=-1),
        'XGBoost': XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.05,
            scale_pos_weight=min(scale_pos_weight, 2.0),
            eval_metric='auc', random_state=RANDOM_SEED,
            n_jobs=-1, verbosity=0),
    }

    skf       = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_SEED)
    cv_results = {}

    for name, model in cv_models.items():
        scores = cross_val_score(
            model, X_train_smote, y_train_smote,
            cv=skf, scoring='roc_auc', n_jobs=-1)
        cv_results[name] = scores
        print(f"\n  {name}:")
        print(f"    Fold AUCs : {[round(s,4) for s in scores]}")
        print(f"    Mean AUC  : {scores.mean():.4f} +/- {scores.std():.4f}")

    # Box plot comparison
    fig, ax = plt.subplots(figsize=(7, 5))
    bp = ax.boxplot(
        [cv_results['Random Forest'], cv_results['XGBoost']],
        labels=['Random Forest', 'XGBoost'],
        patch_artist=True, widths=0.4)
    bp['boxes'][0].set_facecolor('#10B981')
    bp['boxes'][1].set_facecolor('#2563EB')
    for patch in bp['boxes']:
        patch.set_alpha(0.7)
    ax.set_title(f'{n_folds}-Fold CV AUC — Random Forest vs XGBoost',
                 fontsize=12, fontweight='bold')
    ax.set_ylabel('ROC-AUC')
    ax.set_ylim(0.5, 1.0)
    ax.axhline(0.5, color='red', ls='--', lw=1, label='Random baseline')
    ax.legend()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "cv_auc_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\n  Saved: {path}")

    return cv_results


# ============================================================================================================================
# STAGE 7 — Write Best Model Predictions Back to PostgreSQL
# ============================================================================================================================

def write_predictions_to_db(engine, best_model, best_name, best_threshold,
                             X_train, ids_train,
                             X_val,   ids_val,
                             X_test,  ids_test):
    """
    Predict on ALL original rows (no SMOTE — real patients only).
    Write to:
      gold.model_predictions  — full predictions staging table
      gold.kpi_physician      — updates readmission_risk_score column
    """
    print("\n" + "="*70)
    print(f"STAGE 7 — Writing {best_name} predictions to PostgreSQL")
    print("="*70)

    all_X   = pd.concat([X_train, X_val, X_test],      ignore_index=True)
    all_ids = pd.concat([ids_train, ids_val, ids_test], ignore_index=True)
    all_splits = pd.Series(
        ['train']      * len(X_train) +
        ['validation'] * len(X_val)   +
        ['test']       * len(X_test)
    )

    proba_all = best_model.predict_proba(all_X)[:, 1]
    pred_all  = (proba_all >= best_threshold).astype(int)

    predictions = pd.DataFrame({
        'encounter_id'          : all_ids.values,
        'data_split'            : all_splits.values,
        'readmission_risk_score': proba_all.round(4),
        'readmission_predicted' : pred_all,
        'model_name'            : best_name,
        'classification_threshold': round(float(best_threshold), 4),
        'risk_tier'             : pd.cut(
            proba_all,
            bins   = [0.0, 0.2, 0.4, 0.6, 1.001],
            labels = ['Low', 'Moderate', 'High', 'Critical'],
        ).astype(str),
        'predicted_at': pd.Timestamp.now(),
    })

    print(f"\n  Writing {len(predictions):,} predictions to gold.model_predictions...")
    predictions.to_sql(
        name='model_predictions', con=engine, schema='gold',
        if_exists='replace', index=False, method='multi', chunksize=1000)
    print(f"  gold.model_predictions written")

    print(f"\n  Updating gold.kpi_physician.readmission_risk_score...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE gold.kpi_physician kp
            SET    readmission_risk_score = mp.readmission_risk_score
            FROM   gold.model_predictions mp
            WHERE  kp.encounter_id = mp.encounter_id
        """))
        conn.commit()
    print(f"  {result.rowcount:,} rows updated in gold.kpi_physician")

    # Risk tier distribution
    print(f"\n  Risk tier distribution:")
    tier_counts = predictions['risk_tier'].value_counts().sort_index()
    for tier, cnt in tier_counts.items():
        bar = '|' * int(cnt / len(predictions) * 40)
        print(f"    {tier:<10} {cnt:>6,}  {bar}  ({cnt/len(predictions)*100:.1f}%)")

    # Top 10 highest risk patients
    print(f"\n  Top 10 Highest Risk Patients ({best_name}):")
    top10 = pd.read_sql("""
        SELECT
            kp.encounter_id,
            kp.age_group,
            kp.primary_diagnosis_group,
            kp.prior_inpatient_risk_tier,
            kp.glycemic_control_status,
            kp.composite_risk_score,
            ROUND(kp.readmission_risk_score::NUMERIC, 4) AS ml_risk_score,
            mp.risk_tier
        FROM gold.kpi_physician kp
        JOIN gold.model_predictions mp ON kp.encounter_id = mp.encounter_id
        WHERE kp.readmission_risk_score IS NOT NULL
        ORDER BY kp.readmission_risk_score DESC
        LIMIT 10
    """, engine)
    print(top10.to_string(index=False))

    return predictions


# ============================================================================================================================
# BONUS — Save Summary Report
# ============================================================================================================================

def save_summary_report(results, cv_results=None, best_name=None):
    path = os.path.join(OUTPUT_DIR, "model_evaluation_report.txt")
    with open(path, 'w') as f:
        f.write("="*65 + "\n")
        f.write("DIABETES READMISSION MODEL — EVALUATION REPORT\n")
        f.write(f"Generated : {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Pipeline  : SMOTE + Random Forest + XGBoost Comparison\n")
        f.write("="*65 + "\n\n")

        f.write("IMBALANCE STRATEGY\n")
        f.write(f"  Method       : SMOTE\n")
        f.write(f"  Strategy     : {SMOTE_STRATEGY} (minority = {SMOTE_STRATEGY*100:.0f}% of majority)\n")
        f.write(f"  k_neighbors  : {SMOTE_K_NEIGHBORS}\n")
        f.write(f"  Applied to   : Training data ONLY\n\n")

        f.write("MODEL COMPARISON (TEST SET)\n")
        f.write(f"  {'Metric':<22} {'Random Forest':>16} {'XGBoost':>16}\n")
        f.write(f"  {'-'*56}\n")
        for key, label in [('auc','ROC-AUC'),('precision','Precision'),
                            ('recall','Recall'),('f1','F1 Score')]:
            rf  = results['Random Forest'][key]
            xgb = results['XGBoost'][key]
            f.write(f"  {label:<22} {rf:>16.4f} {xgb:>16.4f}\n")

        if best_name:
            f.write(f"\n  Best Model : {best_name}\n\n")

        if cv_results:
            f.write("CROSS-VALIDATION (SMOTE TRAINING DATA)\n")
            for name, scores in cv_results.items():
                f.write(
                    f"  {name:<22} AUC: {scores.mean():.4f} "
                    f"+/- {scores.std():.4f}\n")
            f.write("\n")

        f.write("OUTPUT FILES\n")
        for fname in sorted(os.listdir(OUTPUT_DIR)):
            f.write(f"  {fname}\n")

    print(f"\n  Summary report saved: {path}")


# ============================================================================================================================
# MAIN — Run Full Pipeline
# ============================================================================================================================

def main():
    print("\n" + "="*70)
    print("  DIABETES 130-US HOSPITALS — ML PIPELINE v2.0")
    print("  SMOTE + Random Forest + XGBoost + Model Comparison")
    print("="*70)

    # Connect
    try:
        engine = get_engine()
        with engine.connect() as conn:
            db = conn.execute(text("SELECT current_database()")).scalar()
        print(f"\n  Connected to database: {db}")
    except Exception as e:
        print(f"\n  Connection failed: {e}")
        print(f"  Update DB_CONFIG['password'] at the top of this file.")
        return

    # Stage 1: Load
    df_train, df_val, df_test = load_data(engine)

    # Stage 2: Prepare
    (X_train, y_train, w_train, ids_train,
     X_val,   y_val,   w_val,   ids_val,
     X_test,  y_test,  w_test,  ids_test,
     scale_pos_weight, imputer) = prepare_features(df_train, df_val, df_test)

    feature_names = X_train.columns.tolist()

    # Stage 3: Build multiple imbalance strategy variants
    train_variants = build_resampling_variants(X_train, y_train)
    X_train_smote, y_train_smote = train_variants.get('SMOTE', (X_train, y_train))

    # Cross-Validation on chosen RF training set (SMOTE when available)
    cv_results = cross_validate_both(
        X_train_smote, y_train_smote, scale_pos_weight, n_folds=5)

    # Stage 4: Random Forest
    rf_model = train_random_forest(X_train_smote, y_train_smote, X_val, y_val)

    # Stage 5: XGBoost comparison across imbalance strategies
    xgb_model = train_xgboost(train_variants, X_val, y_val, scale_pos_weight)

    # Stage 6: Evaluate & Compare
    results, best_name, best_model, best_threshold = evaluate_and_compare(
        rf_model, xgb_model, X_val, y_val, X_test, y_test, feature_names)

    # Stage 7: Write to PostgreSQL
    predictions = write_predictions_to_db(
        engine, best_model, best_name, best_threshold,
        X_train, ids_train,
        X_val,   ids_val,
        X_test,  ids_test,
    )

    # Save summary
    save_summary_report(results, cv_results, best_name)

    # Final printout
    print("\n" + "="*70)
    print("  PIPELINE COMPLETE")
    print(f"\n  {'Metric':<22} {'Random Forest':>15} {'XGBoost':>15}")
    print(f"  {'-'*54}")
    for key, label in [('auc','ROC-AUC'),('precision','Precision'),
                       ('recall','Recall'),('f1','F1 Score')]:
        print(f"  {label:<22} {results['Random Forest'][key]:>15.4f} "
              f"{results['XGBoost'][key]:>15.4f}")
    print(f"\n  Best Model      : {best_name}")
    print(f"  Best Threshold  : {best_threshold:.3f}")
    print(f"  Outputs saved   : {os.path.abspath(OUTPUT_DIR)}/")
    print(f"  DB updated      : gold.kpi_physician.readmission_risk_score")
    print("="*70 + "\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
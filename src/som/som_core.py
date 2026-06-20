# ============================================================
# SOM Core — Training, Segmentation, Grid Building
# ============================================================

import pandas as pd
import numpy as np
from minisom import MiniSom
from sklearn.preprocessing import MinMaxScaler
import warnings
from database.connection import DatabaseConnection
from database.schemas import (
    Customer, ProductHolding, SupportInteraction,
    BehavioralSignal, ChurnScore
)
from config.settings import PROCESSED_DATA_DIR
warnings.filterwarnings('ignore')


def load_and_prepare_data() -> pd.DataFrame:
    """
    Query all customer data from the database by joining all five tables
    and return a flat DataFrame ready for SOM training.
    """
    db = DatabaseConnection()

    with db.get_db() as session:
        rows = (
            session.query(
                Customer,
                ProductHolding,
                SupportInteraction,
                BehavioralSignal,
                ChurnScore,
            )
            .join(ProductHolding,     Customer.customer_id == ProductHolding.customer_id)
            .join(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
            .join(BehavioralSignal,   Customer.customer_id == BehavioralSignal.customer_id)
            .join(ChurnScore,         Customer.customer_id == ChurnScore.customer_id)
            .all()
        )

    if not rows:
        raise ValueError("No data returned from database. Check that tables are populated.")

    records = []
    for customer, holding, support, signal, score in rows:
        records.append({
            # Customer
            'age':                      customer.age,
            'tenure_months':            customer.tenure_months,
            'estimated_salary':         customer.estimated_salary,
            'credit_score':             customer.credit_score,
            'is_active_member':         int(customer.is_active_member),
            'has_credit_card':          int(customer.has_credit_card),
            'salary_to_balance_ratio':  customer.salary_to_balance_ratio,
            'geography':                customer.geography.value,
            'gender':                   customer.gender.value,
            'card_type':                customer.card_type.value,
            'segment':                  customer.segment.value,
            'lifecycle_stage':          customer.lifecycle_stage.value,
            'age_band':                 customer.age_band.value,

            # Product Holdings
            'num_products':             holding.num_products,
            'total_balance':            holding.total_balance,
            'product_diversity_score':  holding.product_diversity_score,
            'is_single_product':        int(holding.is_single_product),
            'balance_per_product':      holding.balance_per_product,
            'has_zero_balance':         int(holding.has_zero_balance),

            # Support Interactions
            'has_complaint':            int(support.has_complaint),
            'satisfaction_score':       support.satisfaction_score,
            'complaint_x_satisfaction': support.complaint_x_satisfaction,
            'is_high_risk_support':     int(support.is_high_risk_support),
            'satisfaction_band':        support.satisfaction_band.value,

            # Behavioral Signals
            'points_earned':            signal.points_earned,
            'points_per_tenure':        signal.points_per_tenure,
            'card_engagement_score':    signal.card_engagement_score,
            'activity_drop_flag':       int(signal.activity_drop_flag),

            # Churn Score — target
            'Exited':                   int(score.churned),
        })

    df = pd.DataFrame(records)

    print(f"Loaded {len(df)} customers from database.")
    print(f"Columns: {df.columns.tolist()}")
    print()

    # One-hot encode remaining categorical string columns
    object_cols = df.select_dtypes(include=['object']).columns.tolist()
    print(f"Encoding these string columns: {object_cols}")
    df = pd.get_dummies(df, columns=object_cols, drop_first=False)

    bool_cols = df.select_dtypes(include=['bool']).columns.tolist()
    df[bool_cols] = df[bool_cols].astype(int)

    print(f"\nFinal feature count: {df.shape[1]} columns")
    return df


def scale_features(df):
    X = df.drop('Exited', axis=1).values
    y = df['Exited'].values
    feature_names = df.drop('Exited', axis=1).columns.tolist()

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, feature_names


def train_som(X_scaled, iterations_per_step=100, total_steps=200):
    grid_size = int(np.ceil(np.sqrt(np.sqrt(len(X_scaled)))))
    print(f"\nGrid size: {grid_size} x {grid_size}")

    som = MiniSom(
        x=grid_size,
        y=grid_size,
        input_len=X_scaled.shape[1],
        sigma=1.0,
        learning_rate=0.5,
        random_seed=42
    )

    som.random_weights_init(X_scaled)

    print("Training SOM...")
    qe_history = []

    for i in range(total_steps):
        som.train_random(X_scaled, num_iteration=iterations_per_step, verbose=False)
        qe_history.append(som.quantization_error(X_scaled))
        if (i + 1) % 10 == 0:
            print(f"  Step {i + 1}/{total_steps} — QE: {qe_history[-1]:.4f}")

    print("Training complete.")
    qe = qe_history[-1]
    print(f"\nFinal Quantisation Error: {qe:.4f}")

    return som, grid_size, qe, qe_history


def build_grids(som, grid_size, X_scaled, y):
    bmu_coords  = np.array([som.winner(x) for x in X_scaled])

    churn_grid  = np.zeros((grid_size, grid_size))
    count_grid  = np.zeros((grid_size, grid_size))
    stayed_grid = np.zeros((grid_size, grid_size))

    for coord, label in zip(bmu_coords, y):
        churn_grid[coord[0], coord[1]]  += label
        count_grid[coord[0], coord[1]]  += 1
        stayed_grid[coord[0], coord[1]] += (1 - label)

    count_grid_safe = count_grid.copy()
    count_grid_safe[count_grid_safe == 0] = 1
    churn_rate_grid = churn_grid / count_grid_safe

    return bmu_coords, churn_grid, count_grid, stayed_grid, churn_rate_grid


def assign_risk(rate):
    if rate >= 0.6:
        return 'High Risk'
    elif rate >= 0.3:
        return 'Medium Risk'
    else:
        return 'Low Risk'


def assign_segments(df, bmu_coords, churn_rate_grid):
    df = df.copy()
    df['bmu_x']           = bmu_coords[:, 0]
    df['bmu_y']           = bmu_coords[:, 1]
    df['churn_rate_cell'] = df.apply(
        lambda r: churn_rate_grid[int(r['bmu_x']), int(r['bmu_y'])], axis=1
    )
    df['segment'] = df['churn_rate_cell'].apply(assign_risk)

    print("\nSegment Distribution:")
    print(df['segment'].value_counts())
    print("\nChurn Rate per Segment:")
    print(df.groupby('segment')['Exited'].mean().round(3))

    return df


def save_segmented_data(df):
    output_path = PROCESSED_DATA_DIR / 'customers_segmented.csv'
    df.to_csv(output_path, index=False)
    print(f"\nSegmented dataset saved to {output_path}")


def run_som_pipeline():
    df                               = load_and_prepare_data()
    X_scaled, y, _                   = scale_features(df)
    som, grid_size, qe, qe_history   = train_som(X_scaled)
    bmu_coords, churn_grid, count_grid, stayed_grid, churn_rate_grid = build_grids(
        som, grid_size, X_scaled, y
    )
    df = assign_segments(df, bmu_coords, churn_rate_grid)
    save_segmented_data(df)

    return {
        'df':               df,
        'X_scaled':         X_scaled,
        'y':                y,
        'som':              som,
        'grid_size':        grid_size,
        'qe':               qe,
        'qe_history':       qe_history,
        'bmu_coords':       bmu_coords,
        'churn_grid':       churn_grid,
        'count_grid':       count_grid,
        'stayed_grid':      stayed_grid,
        'churn_rate_grid':  churn_rate_grid,
    }


if __name__ == '__main__':
    run_som_pipeline()
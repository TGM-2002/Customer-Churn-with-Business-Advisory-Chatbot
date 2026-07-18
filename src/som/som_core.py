
# SOM Core — Training, Segmentation, Grid Building

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
    # Pulling every customer's full profile from the database by combining all five tables,
    # Proceeding to  cleaning  and encoding  the data so it is ready to be fed into the SOM.

    # Opening a connection to the database
    db = DatabaseConnection()

    # Joining all five tables together so each row has the full picture of one customer
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

    # Checking if the database returned nothing if so, stop as there is no data to work with moving forward
    if not rows:
        raise ValueError("No data returned from database. Check that tables are populated.")

    # Looping through every customer row and flattening it into a plain dictionary
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

            # Churn Score
            'Exited':                   int(score.churned),
        })

    # Turning the list of dictionariees into a DataFrame
    df = pd.DataFrame(records)

    print(f"Loaded {len(df)} customers from database.")
    print(f"Columns: {df.columns.tolist()}")
    print()

    # Finding any text/category columns and converting them to numbers using one-hot encoding
    object_cols = df.select_dtypes(include=['object']).columns.tolist()
    print(f"Encoding these string columns: {object_cols}")
    df = pd.get_dummies(df, columns=object_cols, drop_first=False)

    # Converting any True/False columns to binary numbers 1/0 so everything is numeric
    bool_cols = df.select_dtypes(include=['bool']).columns.tolist()
    df[bool_cols] = df[bool_cols].astype(int)

    print(f"\nFinal feature count: {df.shape[1]} columns")
    return df


def scale_features(df):
    # Separating the customer features from the churn label and squishes alll
    # feature values into a 0–1 range so no single column has an unfair influence on the SOM.


    # Splitting the data , X = features, y = churn label (0 or 1)
    X = df.drop('Exited', axis=1).values
    y = df['Exited'].values
    feature_names = df.drop('Exited', axis=1).columns.tolist()

    # Scaling every feature to a 0–1 range so no single feature dominates the SOM
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)



    # Returning the scaled features, the labels, and the column namess
    return X_scaled, y, feature_names


def train_som(X_scaled, iterations_per_step=100, total_steps=200):
    # Creating  a self-organising map, trains it on the customer data in small steps and tracks the learning made thus far

    # Working out a sensibleegrid size based on how many customers we have
    grid_size = int(np.ceil(np.sqrt(np.sqrt(len(X_scaled)))))
    print(f"\nGrid size: {grid_size} x {grid_size}")

    # Creatinng the SOM with the calculated grid size and set starting parameters
    som = MiniSom(
        x=grid_size,
        y=grid_size,
        input_len=X_scaled.shape[1],
        sigma=1.0,
        learning_rate=0.5,
        random_seed=42
    )

    # Guving  each neuron a random starting weight drawn from the data
    som.random_weights_init(X_scaled)

    # Training in small steps, recording the error after each step
    print("Training SOM...")
    qe_history = []

    for i in range(total_steps):
        som.train_random(X_scaled, num_iteration=iterations_per_step, verbose=False)
        qe_history.append(som.quantization_error(X_scaled))
        # Printing the  progress update every 10 steps so we can see it is working
        if (i + 1) % 10 == 0:
            print(f"  Step {i + 1}/{total_steps} — QE: {qe_history[-1]:.4f}")

    print("Training complete.")
    qe = qe_history[-1]
    print(f"\nFinal Quantisation Error: {qe:.4f}")

    # Returning the trained SOM along with the grid size, final error, and error history
    return som, grid_size, qe, qe_history


def build_grids(som, grid_size, X_scaled, y):
    # Assigning every customer to their closest SOM neuron (called the BMU) and then we will build three grids: one for churned customers, one for total customers, and one for those who stayed.
    # This will allow us to calculate the churn rate in each cell of the SOM grid.
 

    # Finding the winning neuron (Best Matching Unit) for every single customer
    bmu_coords  = np.array([som.winner(x) for x in X_scaled])

    # Step 2: Set up empty grids to count churned customers, total customers, and those who stayed
    churn_grid  = np.zeros((grid_size, grid_size))
    count_grid  = np.zeros((grid_size, grid_size))
    stayed_grid = np.zeros((grid_size, grid_size))

    # Step 3: Walk through each customer and add them to the right cell in each grid
    for coord, label in zip(bmu_coords, y):
        churn_grid[coord[0], coord[1]]  += label
        count_grid[coord[0], coord[1]]  += 1
        stayed_grid[coord[0], coord[1]] += (1 - label)

    # Step 4: Avoid dividing by zero — replace any empty cells with 1 before dividing
    count_grid_safe = count_grid.copy()
    count_grid_safe[count_grid_safe == 0] = 1

    # Step 5: Calculate the churn rate for each cell (churned ÷ total)
    churn_rate_grid = churn_grid / count_grid_safe

    return bmu_coords, churn_grid, count_grid, stayed_grid, churn_rate_grid


def assign_risk(rate):
    # Takes a churn rate (a number between 0 and 1) and converts it into a
    # human-readable risk label ,High, Medium, or Low Risk.

    # Checking the churn rate and return a risk label
   
    if rate >= 0.6:
        return 'High Risk'# 60% or higher
    elif rate >= 0.3:
        return 'Medium Risk'# 30–59%
    else:
        return 'Low Risk' # below 30%


def assign_segments(df, bmu_coords, churn_rate_grid):
    #Addinjg each customer's SOM position and cell churn rate to the DataFrame,
    # then labeling every customer as High, Medium, or Low Risk based on where they landed on the map.

    # Working on a copy so we do not accidentally change the original DataFrame
    df = df.copy()

    #Recording each customer's winning SOM cell (x, y) and the churn rate of that cell
    df['bmu_x']           = bmu_coords[:, 0]
    df['bmu_y']           = bmu_coords[:, 1]
    df['churn_rate_cell'] = df.apply(
        lambda r: churn_rate_grid[int(r['bmu_x']), int(r['bmu_y'])], axis=1
    )

    # Using the churn rate of the cell to label each customer as High / Medium / Low Risk
    df['segment'] = df['churn_rate_cell'].apply(assign_risk)

    # Printing a quick summary so we can see how customers are spread across segments
    print("\nSegment Distribution:")
    print(df['segment'].value_counts())
    print("\nChurn Rate per Segment:")
    print(df.groupby('segment')['Exited'].mean().round(3))

    return df


def save_segmented_data(df):
    # Writing the fully segmented customer DataFrame to a CSV file on disk
    # so the results can be reused later without re-running the whole pipeline.

    # Building the full file path where the CSV will be saved
    output_path = PROCESSED_DATA_DIR / 'customers_segmented.csv'

    # Writing the DataFrame out as a CSV file 
    df.to_csv(output_path, index=False)
    print(f"\nSegmented dataset saved to {output_path}")


def run_som_pipeline():
    # The main entry point ,runs every stage of the SOM process from start to finish
    # and returns a dictionary containing the trained model, grids, and segmented data.

    # Loading all customer data from the database and prepare it
    df                               = load_and_prepare_data()

    # scaling the features so they are all between 0 and 1
    X_scaled, y, _                   = scale_features(df)

    # =Training SOM on the scaled data
    som, grid_size, qe, qe_history   = train_som(X_scaled)

    # Building the churn grids to see which SOM cells are high or low risk
    bmu_coords, churn_grid, count_grid, stayed_grid, churn_rate_grid = build_grids(
        som, grid_size, X_scaled, y
    )

    # Labellingg each customer with a risk segment based on their SOM cell
    df = assign_segments(df, bmu_coords, churn_rate_grid)

    # Saving the segmented customer data to a CSV for later use
    save_segmented_data(df)

    # Bundling everything into a dictionary and return it for visualisation
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

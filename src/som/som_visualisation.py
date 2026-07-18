
# SOM Visualisation of all the existing Figures

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA
from config.settings import PROCESSED_DATA_DIR

RISK_COLORS = {
    'High Risk':   'tomato',
    'Medium Risk': 'gold',
    'Low Risk':    'mediumseagreen'
}


def fig1_umatrix_overlay(som, grid_size, X_scaled, y):
    # Drawing the U-Matrix — a background heatmap that shows how clustered the SOM neurons are —
    # and overlaying every customer as a dot, coloured by whether they churned or stayed.

    # Creating the figure and set the title
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_title(
        'Figure 1: U-Matrix with Customer Churn Overlay',
        fontsize=15, fontweight='bold', pad=15
    )

    # Computing the U-Matrix ,this shows how far apart neighbouring neurons are
    #         Dark areas mean cluster boundaries, light areas mean customers are similar
    umatrix = som.distance_map().T
    im = ax.pcolor(umatrix, cmap='bone_r', alpha=0.85)
    plt.colorbar(im, ax=ax, label='Neuron Distance (lighter = closer clusters)')

    # Drawing grid lines so each SOM cell is clearly visible
    for x in range(grid_size + 1):
        ax.axvline(x, color='grey', linewidth=0.3, alpha=0.4)
    for y_line in range(grid_size + 1):
        ax.axhline(y_line, color='grey', linewidth=0.3, alpha=0.4)

    # Plotting every customer on top of the U-Matrix
    #         Blue circle = stayed, red square = churned
    markers = ['o', 's']
    colors  = ['royalblue', 'tomato']

    for x_row, label in zip(X_scaled, y):
        bmu = som.winner(x_row)
        ax.plot(
            bmu[0] + 0.5, bmu[1] + 0.5,
            markers[label],
            markerfacecolor='None',
            markeredgecolor=colors[label],
            markersize=5,
            markeredgewidth=1.4,
            alpha=0.55
        )

    # Adding a legend, axis labels, then save and display the chart
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='None',
               markeredgecolor='royalblue', markersize=9, label='Stayed'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='None',
               markeredgecolor='tomato', markersize=9, label='Churned')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11,
              framealpha=0.9, edgecolor='grey')
    ax.set_xlabel('SOM Grid Column', fontsize=12)
    ax.set_ylabel('SOM Grid Row', fontsize=12)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig1_umatrix_overlay.png', dpi=150)
    plt.show()


def fig2_churn_heatmap(churn_rate_grid, count_grid, grid_size):
    # Creating a flat colour-coded grid where each cell shows its churn rate and customer count 
    # red cells are danger zones, green cells are safe, making risk hotspots easy to spot at a glance.

    # Creating the figure and set the title
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_title(
        'Figure 2: Churn Rate Heatmap with Risk Segment Labels',
        fontsize=15, fontweight='bold', pad=15
    )

    # Drawing each SOM cell as a coloured tile — red means high churn, green means low
    im = ax.pcolor(churn_rate_grid.T, cmap='RdYlGn_r', vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label='Churn Rate  (Red = High Risk, Green = Low Risk)')

    # Writing the churn rate and customer count inside each cell so the numbers are readable
    for i in range(grid_size):
        for j in range(grid_size):
            rate  = churn_rate_grid[i, j]
            count = int(count_grid[i, j])
            if count > 0:
                ax.text(
                    i + 0.5, j + 0.7,
                    f"{rate:.2f}",
                    ha='center', va='center',
                    fontsize=7, fontweight='bold', color='black'
                )
                ax.text(
                    i + 0.5, j + 0.3,
                    f"n={count}",
                    ha='center', va='center',
                    fontsize=6, color='dimgrey'
                )

    # Adding axis labels, then save and display the chart
    ax.set_xlabel('SOM Grid Column', fontsize=12)
    ax.set_ylabel('SOM Grid Row', fontsize=12)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig2_churn_heatmap_2d.png', dpi=150)
    plt.show()


def fig3_churn_surface_3d(churn_rate_grid, grid_size):
    # Lifting the churn rate heatmap into 3D so you can see the landscape of risk 
    # tall peaks mean high churn, flat areas mean most customers there are staying.

    # Creating the 3D figure and set the title
    fig = plt.figure(figsize=(13, 9))
    ax  = fig.add_subplot(111, projection='3d')
    ax.set_title(
        'Figure 3: 3D Churn Rate Surface across SOM Grid',
        fontsize=15, fontweight='bold', pad=20
    )

    # Building the x/y grid coordinates and use the churn rate as the height (z axis)
    x_coords       = np.arange(grid_size)
    y_coords       = np.arange(grid_size)
    X_mesh, Y_mesh = np.meshgrid(x_coords, y_coords)
    Z_mesh         = churn_rate_grid.T

    # Drawing the 3D surface ,peaks are high-churn areas, valleys are safe zones
    surf = ax.plot_surface(
        X_mesh, Y_mesh, Z_mesh,
        cmap='RdYlGn_r',
        edgecolor='white',
        linewidth=0.3,
        alpha=0.92
    )

    # Adding a colour bar, label all three axes, tilt the camera to a good angle, then save
    fig.colorbar(surf, ax=ax, shrink=0.45, aspect=10,
                 label='Churn Rate', pad=0.1)
    ax.set_xlabel('SOM Column', fontsize=10, labelpad=10)
    ax.set_ylabel('SOM Row',    fontsize=10, labelpad=10)
    ax.set_zlabel('Churn Rate', fontsize=10, labelpad=10)
    ax.set_zlim(0, 1)
    ax.view_init(elev=30, azim=45)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig3_churn_surface_3d.png', dpi=150)
    plt.show()


def fig4_customers_3d_scatter(df):
    # Plotting every individual customer as a dot in 3D space using their SOM position and
    # cell churn rate, colour-coded by risk segment so you can see how the groups cluster.

    # Creating the 3D figure and set the title
    fig = plt.figure(figsize=(13, 9))
    ax  = fig.add_subplot(111, projection='3d')
    ax.set_title(
        'Figure 4: 3D Customer Distribution by Risk Segment',
        fontsize=15, fontweight='bold', pad=20
    )

    # Looping through each risk segment and plot its customers as coloured dots
    for seg, color in RISK_COLORS.items():
        mask     = df['segment'] == seg
        # Adding a tiny random nudge so overlapping dots do not stack into one blob
        jitter_x = np.random.uniform(-0.25, 0.25, mask.sum())
        jitter_y = np.random.uniform(-0.25, 0.25, mask.sum())
        ax.scatter(
            df.loc[mask, 'bmu_x'] + jitter_x,
            df.loc[mask, 'bmu_y'] + jitter_y,
            df.loc[mask, 'churn_rate_cell'],
            c=color,
            label=seg,
            alpha=0.45,
            s=12,
            edgecolors='none'
        )

    # Adding a legend, label the axes, tilt the camera, then save and display
    ax.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax.set_xlabel('BMU Column',      fontsize=10, labelpad=10)
    ax.set_ylabel('BMU Row',         fontsize=10, labelpad=10)
    ax.set_zlabel('Cell Churn Rate', fontsize=10, labelpad=10)
    ax.set_zlim(0, 1)
    ax.view_init(elev=25, azim=55)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig4_customers_3d_scatter.png', dpi=150)
    plt.show()


def fig5_pca_2d(df, X_scaled):
    # Squashing the many customer features down to just two dimensions using PCA so
    # all customers can be plotted on a simple 2D chart, coloured by their risk segment.

    # Compressing all the customer features down to just 2 dimensions using PCA
    #         This makes it possible to draw every customer on a flat 2D chart
    pca   = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    # Creating the figure and set the title
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_title(
        'Figure 5: PCA 2D Projection of Customer Segments',
        fontsize=15, fontweight='bold', pad=15
    )

    # Plotting each risk segment as coloured dots using the two PCA dimensions
    for seg, color in RISK_COLORS.items():
        mask = df['segment'] == seg
        ax.scatter(
            X_pca[mask, 0],
            X_pca[mask, 1],
            c=color,
            label=f"{seg}  (n={mask.sum()})",
            alpha=0.45,
            s=12,
            edgecolors='none'
        )

    # Labeling axes with how much variance each component explains, add grid and legend
    ax.set_xlabel(
        f"PC1  ({pca.explained_variance_ratio_[0]*100:.1f}% variance explained)",
        fontsize=11
    )
    ax.set_ylabel(
        f"PC2  ({pca.explained_variance_ratio_[1]*100:.1f}% variance explained)",
        fontsize=11
    )
    ax.legend(fontsize=10, framealpha=0.9, edgecolor='grey')
    ax.grid(True, linestyle='--', alpha=0.35)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig5_pca_2d_segments.png', dpi=150)
    plt.show()


def fig6_learning_curve(qe_history, qe, iterations_per_step, total_steps):
    # Showing how the SOM improved over time during training ,the line should drop and
    # flatten out, which means the map stopped changing and settled on a good representation.

    # Creatinmg the figure and set the title
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(
        'Figure 6: SOM Learning Curve (Quantisation Error over Training)',
        fontsize=15, fontweight='bold', pad=15
    )

    #  Drawing the error at each training step as a blue line
    #         A dropping line means the SOM is learning , the neurons are getting closer to the data
    ax.plot(
        [i * iterations_per_step for i in range(1, total_steps + 1)],
        qe_history,
        color='steelblue',
        linewidth=2.5
    )

    # Filling the area under the line to make the trend easier to see
    ax.fill_between(
        [i * iterations_per_step for i in range(1, total_steps + 1)],
        qe_history,
        alpha=0.15,
        color='steelblue'
    )

    # Drawing a red dashed line at the final error so it is easy to read off
    ax.axhline(
        y=qe, color='tomato', linestyle='--',
        linewidth=1.5, label=f"Final QE = {qe:.4f}"
    )

    # Adding axis labels, grid, legend, then save and display
    ax.set_xlabel('Training Iterations', fontsize=12)
    ax.set_ylabel('Quantisation Error', fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig(PROCESSED_DATA_DIR / 'fig6_learning_curve.png', dpi=150)
    plt.show()


def run_all_figures(results):
    # The main entry point for visualisation , takes the output of the SOM pipeline
    # and produces all six charts in one go, saving each as a PNG file.

    #  Unpacking everything from the pipeline results dictionary
    df              = results['df']
    X_scaled        = results['X_scaled']
    y               = results['y']
    som             = results['som']
    grid_size       = results['grid_size']
    qe              = results['qe']
    qe_history      = results['qe_history']
    churn_rate_grid = results['churn_rate_grid']
    count_grid      = results['count_grid']

    #  Generating each figure in order , one call per chart
    fig1_umatrix_overlay(som, grid_size, X_scaled, y)
    fig2_churn_heatmap(churn_rate_grid, count_grid, grid_size)
    fig3_churn_surface_3d(churn_rate_grid, grid_size)
    fig4_customers_3d_scatter(df)
    fig5_pca_2d(df, X_scaled)
    fig6_learning_curve(qe_history, qe, iterations_per_step=100, total_steps=200)

    #  where all the saved image files can be found
    print("\nAll figures saved to:", PROCESSED_DATA_DIR)


if __name__ == '__main__':
    from src.som.som_core import run_som_pipeline
    results = run_som_pipeline()
    run_all_figures(results)

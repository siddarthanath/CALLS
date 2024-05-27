"""
This file stores utility functions, which will be used by other files.
"""
# -------------------------------------------------------------------------------------------------------------------- #

# Standard Library

# Third Party
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Private Party
from src.helper.metrics import mean_squared_error
from src.helper.distmodel import DiscreteDist, GaussDist


# -------------------------------------------------------------------------------------------------------------------- #


def create_dataset(path, num_occurrences_low, num_occurrences_high, temps, num_smiles):
    data = pd.read_csv(path)
    data = data.dropna()
    data = data.drop_duplicates().reset_index(drop=True)
    data.rename(columns={"T,K": "Temperature"}, inplace=True)
    data = data.sort_values(by="SMILES")
    # Shrink dataset
    main_data = pd.DataFrame(columns=["SMILES"] + list(data["Temperature"].unique()))
    for smile in data["SMILES"].unique():
        sub_result = data[data["SMILES"] == smile]
        sub_temp = {"SMILES": smile}
        sub_temp.update(dict(sub_result["Temperature"].value_counts()))
        for temp in list(main_data.columns):
            if temp not in sub_temp.keys():
                sub_temp[temp] = 0
        main_data = pd.concat(
            (pd.DataFrame([sub_temp], columns=list(main_data.columns)), main_data)
        )
    sub_data = main_data[["SMILES"] + temps]
    mask = (sub_data.iloc[:, 1:] > num_occurrences_low) & (
        sub_data.iloc[:, 1:] < num_occurrences_high
    )
    mask = mask.all(axis=1)
    refined_data = sub_data[mask]
    refined_data = refined_data[refined_data.iloc[:, 1:].eq(5).all(axis=1)][:num_smiles]
    combined_data = data.merge(refined_data["SMILES"], on="SMILES")
    combined_data = combined_data[combined_data["Temperature"].isin(temps)]
    # Final dataframe
    combined_data.rename(columns={"SMILES_Solvent": "SMILES Solvent"}, inplace=True)
    combined_df = combined_data[
        ["SMILES", "Temperature", "SMILES Solvent", "Solubility"]
    ].reset_index(drop=True)
    return combined_df

def process_bo_vs_cbo_results(results, selector, component):
    df = pd.DataFrame(columns=["Strategy", "Method", "Selection", f"{component}"])
    i = 0
    for method, method_data in results.items():
        # Iterate through the second-level dictionary
        for lift_type, lift_data in method_data.items():
            # Iterate through the 'Optimal Point with MMR' and 'Optimal Point without MMR' entries
            for j, (mmr_type, mmr_data) in enumerate(lift_data.items()):
                component_values = [
                    point[component] for point in results[method][lift_type][mmr_type]
                ]
                if len(component_values) != 0:
                    df.loc[i] = {
                        "Strategy": method,
                        "Method": lift_type,
                        "Selection": selector[i],
                        f"{component}": component_values,
                    }
                    i += 1
    return df

def plot_component_lists(component_lists, label, avg_label):
    assert is_list_of_floats_or_ints(component_lists)
    plt.figure(figsize=(10, 6))
    # Plot individual regret lists (slightly faded)
    for i, regret_list in enumerate(component_lists):
        plt.plot(np.cumsum(regret_list), alpha=0.5, label=f"{label}")
    # Calculate the average regret list
    avg_cum_regret = np.array(component_lists).mean(axis=0).cumsum()
    # Plot the average regret list (bold)
    plt.plot(
        avg_cum_regret, label=avg_label, linewidth=2.5, linestyle="--", color="black"
    )
    # Add labels and legend
    plt.xlabel("Iteration")
    plt.ylabel("Cumulative Regret")
    plt.title("Regret Over Iterations")
    plt.legend()

def is_list_of_floats_or_ints(lst):
    for inner_lst in lst:
        if not isinstance(inner_lst, list):
            return False
        for item in inner_lst:
            if not isinstance(item, (float, int)):
                return False
    return True

def combine(s, l):
    return s**l - (s - 1) ** (l)


def prob(s, l, n):
    return combine(s, l) * ((1 / n) ** l)

def expected_value_p(l, n):
    E = [s * prob(s, l, n) for s in range(1, 100 + 1)]
    return sum(E)

def expected_value_q(l, n, data):
    quants = [data.quantile(i / 100) for i in range(100 + 1)]
    # E = [(quants[s-1]) * prob(s, l, n) for s in range(1,100+1)]
    E = [((quants[s - 1] + quants[s]) / 2) * prob(s, l, n) for s in range(1, 100 + 1)]
    return sum(E)

def make_dd(values, probs):
    dd = DiscreteDist(values, probs)
    if len(dd) == 1:
        return GaussDist(dd.mean(), None)
    return dd

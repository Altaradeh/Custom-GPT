# ==============================================================================
#                      LONG-TERM PATH SIMULATOR SCRIPT
# ==============================================================================
#
# Purpose:
# This script serves as the final tool for generating and visualizing a set of
# long-term market paths based on a specific, pre-calibrated set of model
# parameters. It is designed to be called by a master application, which would
# fetch a parameter set from the main parameter library (the CSV file).
#
# How it works:
# 1. It takes a defined set of model parameters as input.
# 2. It runs a robust simulation, generating 100 individual 40-year paths.
# 3. It calculates a comprehensive dashboard of summary statistics averaged
#    across all generated paths.
# 4. It generates and displays a summary table showing the price levels for the
#    5th, 50th (mean), and 95th percentiles at 5-year intervals, starting
#    from year 10 as requested.
# 5. It plots a visual envelope of the simulation outcomes, showing the range
#    between the 5th and 95th percentiles, along with the mean path.
#
# ==============================================================================

import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
import os # Added for potential future file operations, though not used in this specific script's output

# ==============================================================================
#                      MODEL FUNCTIONS (FINAL VERSION)
# ==============================================================================

def generate_tanh_ou_path(days, mu, sigma, kappa, beta, S0=1):
    """Generates a baseline path using a tanh-based Ornstein-Uhlenbeck (OU) process."""
    dt = 1 / 252
    log_S0 = np.log(S0)
    X = log_S0
    path = [X]
    for i in range(days):
        t = (i + 1) * dt
        target_mu_t = log_S0 + mu * t
        reversion_force = -kappa * np.tanh(beta * (X - target_mu_t)) * dt
        random_shock = sigma * np.sqrt(dt) * np.random.randn()
        X += reversion_force + random_shock
        path.append(X)
    return np.array(path)

def apply_return_capping(prices, gamma):
    """Applies a soft cap to daily returns."""
    if gamma <= 0: return prices
    safe_prices = np.maximum(prices, 1e-9)
    log_returns = np.diff(np.log(safe_prices))
    capped_log_returns = (1 / gamma) * np.tanh(gamma * log_returns)
    new_prices = np.zeros_like(prices)
    new_prices[0] = prices[0]
    new_prices[1:] = prices[0] * np.exp(np.cumsum(capped_log_returns))
    return new_prices

def simulate_dislocation(total_days, drop_frac, drop_days, rec_days, shape_k=10, recovery_target=1.0):
    """Generates a crisis shock envelope with a variable recovery target."""
    if drop_days <= 0 or rec_days <= 0: return np.ones(total_days)
    decline, recov = np.arange(drop_days), np.arange(rec_days)
    L = lambda x, d: 1/(1 + np.exp(-shape_k * (x/d - 0.5))) if d > 0 else np.zeros_like(x)
    decline_factor = 1 - drop_frac * L(decline, drop_days)
    start_of_recovery = 1 - drop_frac
    end_of_recovery = recovery_target
    recovery_range = end_of_recovery - start_of_recovery
    recovery_factor = start_of_recovery + recovery_range * L(recov, rec_days)
    shock = np.concatenate([decline_factor, recovery_factor])
    full = np.ones(total_days)
    n = min(len(shock), total_days)
    full[:n] = shock[:n]
    return full

def generate_clustered_crisis_events(days, base_minor_rate, base_major_rate, k=12, boost_period=2000, cooldown_period=756):
    """Generates crisis events with clustering and a full cooldown period."""
    events = []
    boosted_minor_until, boosted_major_until, major_cooldown_until = -1, -1, -1
    for day in range(days):
        minor_rate_today = base_minor_rate * (k if day < boosted_minor_until else 1.0)
        major_rate_today = base_major_rate * (k if day < boosted_major_until else 1.0)
        if day < major_cooldown_until:
            major_rate_today, minor_rate_today = 0.0, 0.0
        if np.random.rand() < minor_rate_today:
            events.append((day, 'minor'))
            boosted_minor_until = day + boost_period
        if np.random.rand() < major_rate_today:
            events.append((day, 'major'))
            boosted_major_until = day + boost_period
            major_cooldown_until = day + cooldown_period
    return sorted(events)

def apply_tanh_damping(drop_frac, current_drawdown, threshold=0.5, cap=0.65, alpha=70):
    """Applies a damping factor to a shock based on current drawdown level."""
    if current_drawdown < threshold: return drop_frac
    if current_drawdown >= cap: return 0.0
    return drop_frac * 0.5 * (1 - np.tanh(alpha * (current_drawdown - threshold)))

def count_lost_periods(prices, period_length_years):
    """Counts the number of distinct lost periods of a given length."""
    period_length_days = int(period_length_years * 252)
    if len(prices) < period_length_days: return 0
    highs = np.maximum.accumulate(prices)
    count = 0
    i = 0
    while i <= len(prices) - period_length_days:
        peak = highs[i]
        if prices[i] < peak:
            if not np.any(prices[i : i + period_length_days] >= peak):
                count += 1
                i += period_length_days
            else:
                i += 1
        else:
            i += 1
    return count

def count_distinct_drawdown_events(prices, threshold):
    """Counts distinct drawdown events based on a single threshold."""
    if len(prices) == 0: return 0
    running_max, count, in_drawdown = prices[0], 0, False
    for price in prices[1:]:
        if price > running_max:
            running_max, in_drawdown = price, False
        drawdown = 1 - price / running_max
        if drawdown >= threshold and not in_drawdown:
            count += 1
            in_drawdown = True
    return count

# ==============================================================================
#                      MAIN SIMULATION & REPORTING FUNCTION
# ==============================================================================

def run_and_report_simulation(params):
    """
    Takes a set of model parameters, runs a full simulation, and prints a
    comprehensive report with statistics and plots.
    """
    # Simulation Settings
    n_paths = 100
    years = 40
    days_long = years * 252

    # Data Storage
    path_results = []
    all_price_paths = []

    print(f"--- Generating {n_paths} paths with the specified parameters ---")
    start_time = time.time()

    for i in range(n_paths):
        # Generate a single path
        ou_path = generate_tanh_ou_path(days_long, params['mu'], params['sigma'], params['kappa'], params['beta'])
        base_price_path = np.exp(ou_path)
        
        base_minor_rate = 1 / (params['minor_yrs'] * 252)
        base_major_rate = 1 / (params['major_yrs'] * 252)
        events = generate_clustered_crisis_events(days_long, base_minor_rate, base_major_rate, params['k'])
        
        guaranteed_crisis_day = np.random.randint(252, 252 * 5)
        events.append((guaranteed_crisis_day, 'minor'))
        events = sorted(list(set(events))) # Ensure uniqueness and sort by day
        
        cumulative_shock = np.ones(days_long + 1)
        peak_price = base_price_path[0] # Initialize peak price for drawdown calculation
        for t, typ in events:
            price_before_shock = base_price_path[t] * cumulative_shock[t]
            peak_price = max(peak_price, price_before_shock) # Update overall peak
            current_dd = 1 - (price_before_shock / peak_price)
            if typ == 'minor':
                drop, d_days, r_days = np.random.uniform(0.2,0.35), np.random.randint(20,70), np.random.randint(300,1000)
            else:
                drop, d_days, r_days = np.random.uniform(0.4,0.6), np.random.randint(40,120), np.random.randint(1000,2500)
            
            # Apply damping to the drop_frac based on current drawdown
            damped_drop = apply_tanh_damping(drop, current_dd) 
            
            rec_target = np.random.uniform(1 - params['rec_var'], 1 + params['rec_var'])
            dislocation = simulate_dislocation(days_long + 1 - t, damped_drop, d_days, r_days, recovery_target=rec_target)
            cumulative_shock[t:] *= dislocation
        
        raw_prices = base_price_path * cumulative_shock
        final_prices = apply_return_capping(raw_prices, gamma=params['gamma'])
        all_price_paths.append(final_prices)
        
        # Calculate and store stats for this path
        returns = np.diff(np.log(final_prices))
        daily_pct_change = np.diff(final_prices) / final_prices[:-1]
        max_day_drop = np.min(daily_pct_change) if len(daily_pct_change) > 0 else 0

        path_results.append({
            "annual_return": (final_prices[-1]/final_prices[0])**(1/years)-1,
            "annual_std_dev": np.std(returns) * np.sqrt(252),
            "max_drawdown": 1 - np.min(final_prices / np.maximum.accumulate(final_prices)), # Renamed from max_drop for clarity
            "max_daily_drop": abs(max_day_drop), # Renamed from max_day_drop for clarity
            "lost_years": count_lost_periods(final_prices, 1),
            "lost_five_year_periods": count_lost_periods(final_prices, 5), # Renamed for clarity
            "lost_decades": count_lost_periods(final_prices, 10),
        })

    end_time = time.time()
    print(f"\n--- Simulation Completed in {end_time - start_time:.1f} seconds ---")

    # --- Calculate and Display Final Statistics ---
    avg_results = {key: np.mean([res[key] for res in path_results]) for key in path_results[0]}
    all_returns = [res['annual_return'] for res in path_results]

    print("\n--- FINAL SIMULATION DASHBOARD ---")
    print(f"Averaged over {n_paths} paths:\n")
    print(f"{'Annual Return:':<25} {avg_results['annual_return']:.2%} (Min: {min(all_returns):.2%}, Max: {max(all_returns):.2%})")
    print(f"{'Annualized Std Dev:':<25} {avg_results['annual_std_dev']:.2%}")
    print(f"{'Maximum Drawdown:':<25} {avg_results['max_drawdown']:.2%}") # Updated name
    print(f"{'Max Daily Drop:':<25} {avg_results['max_daily_drop']:.2%}") # Updated name
    print("-" * 40)
    print(f"{'Avg. Lost Years:':<25} {avg_results['lost_years']:.2f}")
    print(f"{'Avg. Lost 5-Year Periods:':<25} {avg_results['lost_five_year_periods']:.2f}") # Updated name
    print(f"{'Avg. Lost Decades:':<25} {avg_results['lost_decades']:.2f}")

    # --- Calculate and Plot Envelope ---
    paths_array = np.array(all_price_paths)
    mean_path = np.mean(paths_array, axis=0)
    p5_path = np.percentile(paths_array, 5, axis=0)
    p95_path = np.percentile(paths_array, 95, axis=0)

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.fill_between(range(len(mean_path)), p5_path, p95_path, color='lightblue', alpha=0.4, label='5th-95th Percentile Envelope')
    ax.plot(mean_path, color='blue', linestyle='--', linewidth=1.5, label='Mean Path')
    ax.set_title(f'Envelope of {n_paths} Simulated Paths', fontsize=16)
    ax.set_xlabel('Days')
    ax.set_ylabel('Simulated Price (Linear Scale)')
    ax.grid(True, which="both", ls="--", alpha=0.4)
    ax.legend(loc='upper left')
    plt.show() # This will display the plot

    # --- Display Summary Table ---
    table_years = np.arange(10, years + 1, 5) # Start table at year 10
    table_indices = [int(y * 252) for y in table_years]
    table_data = {
        'Year': table_years,
        '5th Percentile': p5_path[table_indices],
        'Mean': mean_path[table_indices],
        '95th Percentile': p95_path[table_indices]
    }
    df = pd.DataFrame(table_data)
    print("\n--- Price Envelope Summary Table (starting from Year 10) ---")
    print(df.to_string(index=False, float_format="%.2f"))

# ==============================================================================
#                                  EXECUTION
# ==============================================================================
if __name__ == '__main__':
    # Define the set of calibrated parameters to use for the simulation.
    # In a real application, these would be read from the param_library.csv file.
    calibrated_params = {
        'mu': 0.088, 'sigma': 0.151, 'kappa': 1.32, 'beta': 4.724,
        'minor_yrs': 14.338, 'major_yrs': 33.129, 'k': 8.701,
        'gamma': 13.726, 'rec_var': 0.118
    }
    
    # Run the full simulation and reporting function
    run_and_report_simulation(calibrated_params)
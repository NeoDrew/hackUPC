import pandas as pd
import numpy as np
from scipy import stats
from sklearn.isotonic import IsotonicRegression
import ruptures as rpt
from ..datastore import Datastore

def prepare_fatigue_timeseries(store: Datastore, creative_id: int) -> pd.DataFrame:
    """
    Step 1: Data Preparation for Fatigue ML System.
    Loads the daily impressions/clicks for a creative into a continuous time series.
    Calculates 3-day and 7-day rolling CTR to smooth noise.
    """
    points = store.timeseries_by_creative.get(creative_id)
    if not points:
        # Return empty dataframe with expected columns if no data
        return pd.DataFrame(columns=[
            "date", "impressions", "clicks", "conversions", "spend_usd", "revenue_usd", 
            "ctr", "rolling_3d_ctr", "rolling_7d_ctr"
        ])
    
    df = pd.DataFrame(points)
    
    # Ensure date is datetime and sorted
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # Calculate raw daily CTR (safeguard against div by zero)
    df["ctr"] = (df["clicks"] / df["impressions"].replace(0, 1)).fillna(0)
    
    # Calculate rolling sums for impressions and clicks to compute accurate rolling CTR
    # We use min_periods=1 so we get a value even in the first few days
    rolling_3d_imp = df["impressions"].rolling(window=3, min_periods=1).sum()
    rolling_3d_clk = df["clicks"].rolling(window=3, min_periods=1).sum()
    df["rolling_3d_ctr"] = (rolling_3d_clk / rolling_3d_imp.replace(0, 1)).fillna(0)
    
    rolling_7d_imp = df["impressions"].rolling(window=7, min_periods=1).sum()
    rolling_7d_clk = df["clicks"].rolling(window=7, min_periods=1).sum()
    df["rolling_7d_ctr"] = (rolling_7d_clk / rolling_7d_imp.replace(0, 1)).fillna(0)
    
    return df

def identify_fatigue_changepoint(df: pd.DataFrame, alpha: float = 0.05) -> dict:
    """
    Step 2 & 3: Model Integration & Statistical Filter.
    Fits Isotonic Regression, finds changepoint, then applies a Beta-binomial
    difference-of-proportions test to ensure the drop is statistically significant.
    """
    # Initialize default structure including Step 3 fields
    base_result = {
        "is_fatigued": False, 
        "predicted_fatigue_day": None, 
        "predicted_fatigue_date": None,
        "fatigue_ctr_drop": None,
        "p_value": None,
        "is_significant": False
    }

    if df.empty or len(df) < 14:
        return base_result

    # Extract our signal signal: rolling_7d_ctr
    signal = df["rolling_7d_ctr"].values

    # Step 2a: Fit Isotonic Regression to strictly enforce non-increasing CTR trend
    iso = IsotonicRegression(increasing=False, out_of_bounds='clip')
    smoothed_signal = iso.fit_transform(np.arange(len(signal)), signal)
    
    df["smoothed_ctr_decay"] = smoothed_signal

    # Step 2b: Changepoint Detection via Ruptures (Binary Segmentation)
    algo = rpt.Binseg(model="l2").fit(smoothed_signal)
    
    try:
        breakpoints = algo.predict(n_bkps=1)
    except Exception:
        return base_result

    bkp_idx = breakpoints[0]

    if 5 <= bkp_idx < len(signal) - 1:
        baseline_ctr = float(np.mean(smoothed_signal[:bkp_idx]))
        post_break_ctr = float(np.mean(smoothed_signal[bkp_idx:]))
        
        if baseline_ctr > 0:
            drop_ratio = post_break_ctr / baseline_ctr
            
            if drop_ratio < 0.75: # e.g. a >25% drop relative to early baseline
                
                # Step 3: Beta-Binomial Difference of Proportions Test
                pre_impressions = df["impressions"].iloc[:bkp_idx].sum()
                pre_clicks = df["clicks"].iloc[:bkp_idx].sum()
                
                post_impressions = df["impressions"].iloc[bkp_idx:].sum()
                post_clicks = df["clicks"].iloc[bkp_idx:].sum()
                
                # Setup Beta distributions (Prioring with Alpha=1, Beta=1 uniform)
                a_pre, b_pre = 1 + pre_clicks, 1 + pre_impressions - pre_clicks
                a_post, b_post = 1 + post_clicks, 1 + post_impressions - post_clicks
                
                # Monte Carlo sampling for Beta-Binomial
                n_samples = 10000
                pre_samples = stats.beta.rvs(a_pre, b_pre, size=n_samples)
                post_samples = stats.beta.rvs(a_post, b_post, size=n_samples)
                
                # p-value = Probability that Post CTR >= Pre CTR (Null hypothesis: no drop)
                p_val = float(np.mean(post_samples >= pre_samples))
                is_sig = p_val < alpha
                
                # Only commit to the classification if statistically significant
                predicted_date = df.iloc[bkp_idx]["date"].strftime('%Y-%m-%d')
                
                return {
                    "is_fatigued": bool(is_sig), 
                    "predicted_fatigue_day": int(bkp_idx) if is_sig else None, 
                    "predicted_fatigue_date": predicted_date if is_sig else None,
                    "fatigue_ctr_drop": float(1.0 - drop_ratio) if is_sig else None,
                    "p_value": p_val,
                    "is_significant": bool(is_sig)
                }
                
    return base_result


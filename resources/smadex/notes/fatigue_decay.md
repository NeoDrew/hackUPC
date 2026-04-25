### fatigue decay notes

## input
| Column                         | Role                                                                        |
| ------------------------------ | --------------------------------------------------------------------------- |
| creative_id + date             | Primary keys                                                                |
| days_since_launch              | Timeline anchor (avoids date-alignment issues across creatives)             |
| impressions                    | Denominator for all rate metrics                                            |
| clicks → CTR                   | First metric to show fatigue                                                |
| conversions → CVR              | Secondary signal; lags CTR by a few days                                   |
| revenue_usd / spend_usd → ROAS | Final financial decay signal                                                |
| video_completions → VTR        | For rewarded_video and playable formats only                                |
| impressions_last_7d            | Use as a feature only, never sum it — it's a rolling window [dataset notes] |

- can be even better with metadata of each creative

## options

# layered detection method
- compare effectiveness of first 7 days to the last (most recent) 7 days

# linear regression
- method for fitting best straight line through data
    - measures how target variable changes as input varible changes (target: CTR (clicks), input: days since launch (as the creative gets older, does the CTR generally move up or down?))
    - output is lope, which tells you direction and rate of change
    - check whether CTR (smoothed) trend is rising, flat or falling over time
- model y =mx+C relationship 
    -  bruv its just best line of fit u forgot lmao
    - done via least-squares method fit

implementation:
- create 7-day rolling average CTR per creative
- smooths short-term noise (common in time-series analysis); makes underlying trend easier to see
- fits regression with days_since_launch on x and ctr_7d on y axis

output:
- reading slope + p-val (test whether observed slope is real vs random fluctuation)
    - slope -> average change in 7-day CTR for each extra day since launch
    - neg slope -> slope trending downwards
- use pval to determine whether slope is statistically significant under regression test (only flagged if p_value < 0.05)
    - only flag sig slopes (<0.05)     

## compound signals
- CPM rising and CTR falling
    - paying for more impressions while getting fewer clicks
    - highlights both cost and engagement side are falling


- rolling mean removes noise, regression measures direction, and p-value filters for confidence



todos:
- test how effective the model is
- explain why it is fatigued (possibly using LLM)
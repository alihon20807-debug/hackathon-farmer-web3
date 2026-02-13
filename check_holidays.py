import sys
from prophet.make_holidays import make_holidays_df

with open('holidays_log_mh.txt', 'w') as f:
    sys.stdout = f
    print("Holidays included for India (Maharashtra):")
    year_list = list(range(2020, 2027))
    # Note: Prophet's add_country_holidays uses the holidays package.
    # We can try to see if we can pass state to make_holidays_df or how it's handled.
    # Actually make_holidays_df doesn't directly take state in older versions of prophet, 
    # but we can check if 'IN' is enough or if we need custom.
    
    import holidays
    india_holidays = holidays.India(years=year_list, subdiv='MH')
    for date, name in sorted(india_holidays.items()):
        print(f"{date}: {name}")

    print("\nUnique Holiday Names in MH:")
    unique_h = set(india_holidays.values())
    for h in sorted(unique_h):
        print(f"- {h}")

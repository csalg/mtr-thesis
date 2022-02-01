# There is no numeric value for 'never' so we impute it to a very large number
NEVER = 5*30*24*60*60 # 100 years in seconds
# NEVER = 150*24*60*60 # 5 months in seconds
OUTLIERS_COEFFICIENT = 2.5

# Filename to use as repository pickle persistence.
REPOSITORY_FILENAME = "repository.pkl"
SCALER_FILENAME = "scaler.pkl"
DEBUG = True
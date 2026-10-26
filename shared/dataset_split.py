from math import ceil
import pandas as pd
from sklearn.model_selection import train_test_split
from shared.modeling import TrainingInput
from shared.dataset_validation import validate_dataset

def split_dataset(
    df: pd.DataFrame,training_input: TrainingInput, )-> tuple[pd.DataFrame, pd.DataFrame, pd.Series , pd.Series]:
  #check the dataset before attempting to split it
  validate_dataset(df, training_input)

  X = df[training_input.feature_columns].copy()
  y = df[training_input.target_column].copy()

  # Calculate the number of samples for the test set
  n_test = ceil(len(df) * training_input.test_size)
  n_train = len(df)-n_test

  #our workflow requires that the training set has at least 2 samples per class, so we will check for that and raise an error if it is not met
  if n_train < 2 or n_test<2:
    raise ValueError(
      "Training and test sets must each contain at least 2 rows. Add more or review test_size."
    )
  stratify_labels = None
  if training_input.task_type == "classification":
    class_counts = y.value_counts()
    n_classes = len(class_counts)

    #A class needs multiple examples to appear in both sets
    if class_counts.min()<2:
      raise ValueError("Every class must contain at least two examples for a stratified split.")

    if n_train < n_classes or n_test < n_classes:
      raise ValueError(
        f"There are{n_classes} classes, but the requested split creates {n_train} training rows and {n_test} test rows. Each set needs at least {n_classes} rows"
      )

    stratify_labels = y

  X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=n_test,
        random_state=training_input.random_state,
        shuffle=True,
        stratify=stratify_labels,
    )

  if training_input.task_type == "classification":
      expected_classes = set(y.unique())

      if(
        set(y_train.unique()) != expected_classes or set(y_test.unique()) != expected_classes):
        raise ValueError("Some classes are missing from the split. Add more examples of rare classes or review the train/test proportions.")

  return X_train, X_test, y_train, y_test

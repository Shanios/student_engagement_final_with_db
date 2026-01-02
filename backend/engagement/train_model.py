import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# Load feature dataset
X = np.load("X_features.npy")
y = np.load("y_labels.npy")

# Encode labels (engaged = 1, not_engaged = 0)
y_encoded = np.array([1 if label == "engaged" else 0 for label in y])

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Build classifier
model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    max_depth=10
)

# Train model
model.fit(X_train, y_train)

# Test model
y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save trained model
joblib.dump(model, "engagement_model.pkl")
print("\nModel saved as engagement_model.pkl")

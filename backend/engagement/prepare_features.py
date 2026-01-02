import pandas as pd
import numpy as np

# ====== CONFIG ======
CSV_PATH = "ear_dataset.csv"       # your collected data
WINDOW_SIZE = 30                   # 30 frames = ~1 second
EAR_THRESHOLD = 0.18               # used for "fraction below threshold"
# =====================

def extract_features_from_window(window):
    ear_values = window["ear"].values
    label = window["label"].values[-1]  # label of last row in window

    # Features:
    mean_ear = np.mean(ear_values)
    std_ear = np.std(ear_values)
    min_ear = np.min(ear_values)
    max_ear = np.max(ear_values)
    fraction_below = np.sum(ear_values < EAR_THRESHOLD) / len(ear_values)

    return [mean_ear, std_ear, min_ear, max_ear, fraction_below], label


def main():
    df = pd.read_csv(CSV_PATH)

    features = []
    labels = []

    # Sliding window feature extraction
    for start in range(0, len(df) - WINDOW_SIZE):
        window = df.iloc[start:start + WINDOW_SIZE]

        # Skip unlabeled windows
        if any(window["label"].isnull()) or any(window["label"] == "None"):
            continue

        feature_vec, label = extract_features_from_window(window)

        features.append(feature_vec)
        labels.append(label)

    features = np.array(features)
    labels = np.array(labels)

    # Save for training
    np.save("X_features.npy", features)
    np.save("y_labels.npy", labels)

    print("Feature extraction complete!")
    print("Saved X_features.npy and y_labels.npy")
    print(f"Total samples: {len(features)}")


if __name__ == "__main__":
    main()

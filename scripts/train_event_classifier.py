"""
Train event classification model from tuntun-news dataset.
11 classes: Delisting, Dividend, Expansion, IPO, M&A, 
Private Placement, Rights Issue, Buyback, Spin-off, Stock Split, Tender Offer

Uses TF-IDF + LogisticRegression — lightweight, no GPU needed.
"""
import json
import pickle
import os
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "events"
MODEL_DIR = PROJECT_ROOT / "data" / "models" / "event_classifier"

def load_data():
    """Load train/val/test CSV files."""
    train = pd.read_csv(DATA_DIR / "train.csv")
    val = pd.read_csv(DATA_DIR / "validation.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    
    with open(DATA_DIR / "labels.json") as f:
        label_map = json.load(f)
    
    return train, val, test, label_map

def clean_text(text: str) -> str:
    """Basic text cleaning."""
    if pd.isna(text):
        return ""
    # Lowercase, remove excessive whitespace
    text = str(text).lower().strip()
    text = ' '.join(text.split())
    return text

def train_model(X_train, y_train):
    """Train TF-IDF + LogisticRegression pipeline."""
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=15000,
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.9,
            sublinear_tf=True
        )),
        ('clf', LogisticRegression(
            C=5.0,
            max_iter=1000,
            solver='lbfgs'
        ))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

def main():
    print("=" * 50)
    print("Training Event Classification Engine")
    print("=" * 50)
    
    # Load data
    train, val, test, label_map = load_data()
    print(f"\nTrain: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    print(f"Labels: {label_map}")
    
    # Clean text
    train['text'] = train['text'].apply(clean_text)
    val['text'] = val['text'].apply(clean_text)
    test['text'] = test['text'].apply(clean_text)
    
    # Combine train+val for final model
    X = pd.concat([train, val])
    X_text = X['text'].values
    y = X['label'].values
    
    X_test = test['text'].values
    y_test = test['label'].values
    
    # Train
    print("\nTraining TF-IDF + LogisticRegression...")
    model = train_model(X_text, y)
    
    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\n🎯 Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print("\n" + classification_report(
        y_test, y_pred,
        target_names=[label_map[str(i)] for i in range(len(label_map))],
        zero_division=0
    ))
    
    # Save model
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    model_path = MODEL_DIR / "event_classifier.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    label_path = MODEL_DIR / "labels.json"
    with open(label_path, 'w') as f:
        json.dump(label_map, f, indent=2, ensure_ascii=False)
    
    # Save label encoder mapping (for reverse lookup)
    id_to_label = {int(k): v for k, v in label_map.items()}
    with open(MODEL_DIR / "id_to_label.json", 'w') as f:
        json.dump(id_to_label, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Model saved to {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")
    print(f"   Labels saved to {label_path}")
    
    # Quick demo
    print("\n" + "=" * 50)
    print("Quick Demo Predictions")
    print("=" * 50)
    demos = [
        "PT Telkom Tbk mengumumkan pembagian dividen tunai sebesar Rp 14 triliun",
        "Perusahaan resmi delisting dari Bursa Efek Indonesia",
        "GoTo akan melakukan IPO di Bursa Efek Indonesia tahun ini",
        "Bank Mandiri melakukan buyback saham senilai Rp 5 triliun",
        "Produsen semen buka pabrik baru di Sulawesi",
        "Emiten properti akuisisi lahan strategis di Jakarta",
    ]
    for demo in demos:
        pred = model.predict([clean_text(demo)])[0]
        proba = model.predict_proba([clean_text(demo)])[0]
        confidence = max(proba) * 100
        print(f"  [{id_to_label[pred]}] ({confidence:.1f}%) — {demo}")

if __name__ == "__main__":
    main()

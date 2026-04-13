import os, re, json, numpy as np, pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib, warnings
warnings.filterwarnings("ignore")


def build_dataset():
    np.random.seed(42)
    dep = [
        "I feel so empty inside, nothing brings me joy anymore",
        "I can't sleep at night, my mind races with dark thoughts",
        "Everything feels hopeless, I don't see the point in trying",
        "I've lost interest in activities I used to enjoy",
        "I feel worthless and like a burden to everyone around me",
        "My energy is completely drained, I can barely get out of bed",
        "I cry almost every day and I don't know why",
        "I feel disconnected from everyone, even my closest friends",
        "Nothing matters anymore, life feels meaningless",
        "I'm constantly tired but can't seem to rest",
        "I feel like I'm drowning in sadness with no way out",
        "Every day feels the same, gray and without purpose",
        "I can't concentrate on anything, my mind feels foggy",
        "I feel so alone even when surrounded by people",
        "I've been having trouble eating, nothing tastes good",
        "I feel guilty about everything, even things I can't control",
        "My self-esteem has hit rock bottom lately",
        "I feel like I'm just going through the motions of life",
        "I can't stop thinking about all my failures",
        "I feel numb, like I can't feel anything at all",
        "I have no motivation to do anything productive",
        "I keep cancelling plans because I just can't face people",
        "My anxiety is overwhelming and paralyzing me",
        "I haven't felt happy in months, maybe longer",
        "I spend most of my time in bed staring at the ceiling",
        "I feel trapped in my own mind with no escape",
        "Everything irritates me and I snap at people I love",
        "I've been having recurring nightmares about failing",
        "I feel like I'm watching life pass me by from the outside",
        "I can't remember the last time I genuinely laughed",
        "My chest feels heavy all the time like something is pressing down",
        "I avoid mirrors because I hate what I see",
        "I feel like nobody truly understands what I'm going through",
        "I've been neglecting my personal hygiene and I don't care",
        "I feel crushed by the weight of everyday responsibilities",
        "I've withdrawn from social media because it makes me feel worse",
        "I feel permanently broken and unfixable",
        "I can't find a reason to be optimistic about the future",
        "Every small task feels like climbing a mountain",
        "I feel like I'm suffocating under invisible pressure",
        "I've lost my appetite completely these past weeks",
        "I feel detached from reality like I'm in a fog",
        "I keep replaying painful memories over and over",
        "I feel like a failure in every aspect of my life",
        "I don't recognize myself anymore in the mirror",
        "I feel paralyzed by indecision about the smallest things",
        "I've been isolating myself from family and friends",
        "I wake up dreading the day ahead every single morning",
        "I can't stop the negative thoughts spiraling in my head",
        "I feel like I'm pretending to be okay when I'm not",
        "My body aches constantly and I have no energy",
        "I feel abandoned by everyone who once cared about me",
        "I've given up on my goals and dreams completely",
        "I feel like I'm slowly fading away from existence",
        "I can't enjoy music or movies like I used to",
        "I feel constant dread about things that haven't happened",
        "I'm exhausted from trying to appear normal around others",
        "I feel like my life has no direction or meaning",
        "I don't see any future for myself at all",
        "I feel like a shadow of who I used to be",
    ]
    nondep = [
        "Had a wonderful morning jog in the park today",
        "I'm excited about starting my new project at work",
        "Spent quality time with friends over a delicious dinner",
        "Feeling grateful for the beautiful weather this weekend",
        "Just finished reading an amazing book, highly recommend it",
        "My kids made me laugh so hard today with their jokes",
        "I'm looking forward to the concert this Friday",
        "Completed my workout routine and feeling energized",
        "Had a productive day at work and accomplished my goals",
        "Enjoyed a peaceful walk by the river this evening",
        "I'm thankful for the support of my loving family",
        "Just got promoted at work, hard work pays off",
        "Spent the afternoon gardening and it was so relaxing",
        "I love cooking new recipes and sharing them with friends",
        "The sunset today was absolutely breathtaking",
        "I'm feeling motivated to learn something new this month",
        "Had a great conversation with an old friend today",
        "My morning meditation really helps me start the day right",
        "I appreciate the little things in life more each day",
        "Just booked a vacation and can't wait to explore",
        "Feeling accomplished after finishing a challenging puzzle",
        "I enjoyed volunteering at the community center today",
        "My team won the match and we celebrated together",
        "I'm making progress on my fitness goals every week",
        "Had a lovely picnic with the family at the park",
        "I feel confident about my upcoming presentation",
        "Just adopted a puppy and he's bringing so much joy",
        "I'm proud of how far I've come this year",
        "Enjoyed learning a new dance routine today",
        "The coffee this morning was absolutely perfect",
        "I finally organized my workspace and it feels great",
        "Spent the evening watching stars with my partner",
        "I'm grateful for good health and happiness",
        "Just completed a 5K run, feeling accomplished",
        "I love spending Sunday mornings at the farmers market",
        "My garden is blooming beautifully this spring",
        "Had an inspiring conversation with my mentor today",
        "I'm feeling creative and started painting again",
        "The kindness of strangers always restores my faith",
        "I enjoy starting each day with a positive affirmation",
        "Feeling recharged after a relaxing weekend getaway",
        "I'm excited to try the new restaurant that just opened",
        "Just learned to play a new song on the guitar",
        "I appreciate having meaningful work that I enjoy",
        "Had a wonderful time at the art gallery today",
        "My morning routine sets such a positive tone for the day",
        "I'm grateful for the opportunities coming my way",
        "Spent the day hiking and the views were incredible",
        "I feel at peace with where I am in life right now",
        "Just had the most refreshing swim at the beach",
        "I'm inspired by the progress of my students",
        "Had a heartwarming reunion with college friends",
        "I love the feeling of accomplishment after a good day",
        "The autumn colors are making my walks so beautiful",
        "I'm enjoying learning to cook international cuisines",
        "Feeling blessed to have such supportive colleagues",
        "Just finished redecorating my room and I love it",
        "I'm looking forward to celebrating my birthday",
        "Had a fulfilling day helping at the food bank",
        "I feel optimistic about the future and new possibilities",
    ]

    texts = dep + nondep
    labels = [1]*len(dep) + [0]*len(nondep)
    for t in dep[:30]:
        for p in ["Today ", "Lately "]:
            texts.append(p + t.lower())
            labels.append(1)
    for t in nondep[:30]:
        for p in ["Really ", "Today "]:
            texts.append(p + t.lower())
            labels.append(0)
    df = pd.DataFrame({"text": texts, "label": labels})
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def run_pipeline():
    df = build_dataset()
    df = df.dropna(subset=["text", "label"]).drop_duplicates(subset=["text"])
    df["cleaned_text"] = df["text"].apply(clean_text)
    df = df[df["cleaned_text"].str.len() > 10]
    df["label"] = df["label"].astype(int)

    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True)
    X = tfidf.fit_transform(df["cleaned_text"])
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
        "Linear SVM": LinearSVC(max_iter=1000, random_state=42, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced"),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5),
    }

    results = {}
    best_f1, best_name, best_model = 0, "", None

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        f1 = f1_score(y_test, pred, average="weighted")
        results[name] = {
            "accuracy": round(accuracy_score(y_test, pred), 4),
            "precision": round(precision_score(y_test, pred, average="weighted", zero_division=0), 4),
            "recall": round(recall_score(y_test, pred, average="weighted", zero_division=0), 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        }
        if f1 > best_f1:
            best_f1, best_name, best_model = f1, name, model

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    param_grid = {"C": [0.01, 0.1, 1, 10], "penalty": ["l2"], "solver": ["lbfgs"]}
    gs = GridSearchCV(LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
                      param_grid, cv=cv, scoring="f1_weighted", n_jobs=-1)
    gs.fit(X_train, y_train)
    tuned = gs.best_estimator_
    pred_tuned = tuned.predict(X_test)

    tuned_results = {
        "best_params": gs.best_params_,
        "best_cv_score": round(gs.best_score_, 4),
        "test_accuracy": round(accuracy_score(y_test, pred_tuned), 4),
        "test_precision": round(precision_score(y_test, pred_tuned, average="weighted", zero_division=0), 4),
        "test_recall": round(recall_score(y_test, pred_tuned, average="weighted", zero_division=0), 4),
        "test_f1": round(f1_score(y_test, pred_tuned, average="weighted", zero_division=0), 4),
        "confusion_matrix": confusion_matrix(y_test, pred_tuned).tolist(),
    }

    model_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(tuned, os.path.join(model_dir, "kansi_ai_model.pkl"))
    joblib.dump(tfidf, os.path.join(model_dir, "tfidf_vectorizer.pkl"))

    all_results = {
        "model_name": best_name, "training_date": datetime.now().isoformat(),
        "model_comparison": results, "tuned_results": tuned_results,
    }
    with open(os.path.join(model_dir, "training_results.json"), "w") as f:
        json.dump(all_results, f, indent=2)

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    df.to_csv(os.path.join(data_dir, "cleaned_dataset.csv"), index=False)

    return all_results


if __name__ == "__main__":
    r = run_pipeline()
    print(f"Best model: {r['model_name']}")
    print(f"Tuned F1: {r['tuned_results']['test_f1']}")

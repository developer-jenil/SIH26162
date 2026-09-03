"""Honest spatial-block evaluation utilities."""
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.model_selection import GroupKFold


def spatial_metrics(estimator, X, y, groups, splits=5):
    predictions=np.empty(len(y),dtype=object); probabilities=np.zeros((len(y),len(np.unique(y))))
    cv=GroupKFold(n_splits=min(splits,len(np.unique(groups))))
    for tr,te in cv.split(X,y,groups):
        estimator.fit(X.iloc[tr],y.iloc[tr]); predictions[te]=estimator.predict(X.iloc[te]); probabilities[te]=estimator.predict_proba(X.iloc[te])
    return {"accuracy":accuracy_score(y,predictions),"macro_f1":f1_score(y,predictions,average="macro"),"log_loss":log_loss(y,probabilities)}


def conformal_coverage(conf, lo, hi):
    conf=np.asarray(conf); return float(np.mean((conf>=np.asarray(lo))&(conf<=np.asarray(hi))))

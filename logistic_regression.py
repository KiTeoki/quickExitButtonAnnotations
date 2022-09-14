# Importing libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression
import statsmodels.api as sm
from math import e, exp, log
from sys import exit

def compute_logreg_stats(coef, std_err):
    return pow(e, coef), pow(e, coef - (1.96 * std_err)), pow(e, coef + (1.96 * std_err))

if __name__ == '__main__':
    data = pd.read_csv("logistic_regression_info.csv")
    # Divide the data to training set and test set
    x_cols = [
        "Size_text","Size_small","Size_average","Size_wide","Size_long","Size_large",
        "Location_top_left","Location_top","Location_top_right","Location_left","Location_content","Location_right","Location_bottom_left","Location_bottom","Location_bottom_right","Location_dropdown","Location_menu",
        "Type_button","Type_banner","Type_image_icon","Type_menu_item","Type_text",
        "Sticky","Labelled","Single_click",
        "Visible_yes","Visible_covered","Visible_no",
    ]
    y_cols = [
        "button-discover","button-distinct","learn_button_time","recall_button_time",
        #"shortcut-discover","shortcut-intuitive","learn_shortcut_time","recall_shortcut_time",
        #"text-discover","text-comprehend",
        #"safety-discover","learn_explainer_time","recall_explainer_time"
    ]
    for ycol in y_cols:
        X = data[x_cols]
        print(ycol)
        if "time" in ycol:
            # Timing test
            y = data[ycol] < 10
        else:
            # Likert
            y = data[ycol] > 0

        # Pick out best factors
        logreg = LogisticRegression()
        rfe = RFE(logreg)
        rfe = rfe.fit(X, y)
        chosen = np.array(x_cols)[rfe.support_]
        X = data[chosen]

        # See stats for chosen factors
        logit_model = sm.Logit(y, X)
        result = logit_model.fit(method='minimize', maxiter=500)
        print(result.summary())
        print(f"chi2:{result.llr}, p value: {result.llr_pvalue}")

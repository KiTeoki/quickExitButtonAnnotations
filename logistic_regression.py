# Importing libraries
import csv
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression
import statsmodels.api as sm
from math import e, exp, log
from sys import exit
from scipy.spatial import KDTree
from webcolors import (
    CSS3_HEX_TO_NAMES,
    hex_to_rgb,
)
from agreement import load_survey_data

def compute_logreg_stats(coef, std_err):
    o, l, h = pow(e, coef), pow(e, coef - (1.96 * std_err)), pow(e, coef + (1.96 * std_err))
    return f"{o:.3f} & {l:.3f} & {h:.3f} \\"

# Load timing test results, computing mean time taken for each test
def load_timing_data():
    responses = {}
    # Filenames temporarily blinded
    for filename in ['evaluation1.json', 'evaluation2.json']:
        with open(filename, 'r') as annotations_file:
            parsed_json = json.load(annotations_file)
            # name = parsed_json['name']
            annotations = parsed_json['evaluated']
            for site in annotations:
                url = site['url']
                platform = 'Mobile' if site['is_mobile'] else 'Desktop'
                if (url, platform) not in responses:
                    responses[(url, platform)] = {}
                timings = ['learn_button_time', 'recall_button_time', 'learn_shortcut_time', 'recall_shortcut_time',
                           'learn_explainer_time', 'recall_explainer_time']
                for test in timings:
                    if test in site and site[test] > 0:
                        if test in responses[(url, platform)] and responses[(url, platform)][test] > 0.1:
                            responses[(url, platform)][test] = (responses[(url, platform)][test]+site[test]) / 2.0
                        else:
                            responses[(url, platform)][test] = site[test]
    return responses

def convert_rgb_to_names(rgb_hex):
    if rgb_hex == 'Transparent':
        return 'Transparent'
    rgb_tuple = hex_to_rgb(rgb_hex)
    # a dictionary of all the hex and their respective names in css3
    css3_db = CSS3_HEX_TO_NAMES
    names = []
    rgb_values = []
    for color_hex, color_name in css3_db.items():
        names.append(color_name)
        rgb_values.append(hex_to_rgb(color_hex))

    kdt_db = KDTree(rgb_values)
    distance, index = kdt_db.query(rgb_tuple)
    return names[index]

def likert_to_number(hr_score):
    if hr_score == 'Strongly agree':
        return 2
    elif hr_score == 'Somewhat agree':
        return 1
    elif hr_score == 'Somewhat disagree':
        return -1
    elif hr_score == 'Strongly disagree':
        return -2
    else:
        # Both neither agree nor disagree and error case
        return 0

# Combine both sets of annotations with site data to get dataset of all information about sites
def combine_data():
    destination_filename = "logistic_regression_info.csv"

    # Load likert scale annotations
    likerts = load_survey_data()
    # Load timing annotations
    timings = load_timing_data()

    # Load site data and combine data for each site
    with open(destination_filename, 'w', newline='') as df:
        df.write("URL,Platform,"+#Colour,Background Colour,
                 "Size_text,Size_small,Size_average,Size_wide,Size_long,Size_large,"+
                 "Location_top_left,Location_top,Location_top_right,Location_left,Location_content,Location_right,"+
                 "Location_bottom_left,Location_bottom,Location_bottom_right,Location_dropdown,Location_menu,"+
                 "Type_button,Type_banner,Type_image_icon,Type_menu_item,Type_text,"+
                 "Sticky,Visible_yes,Visible_covered,Visible_no,Labelled,Single_click,"+#Keys,
                 "button-discover,button-distinct,shortcut-discover,shortcut-intuitive,text-discover,text-comprehend,"+
                 "safety-discover,learn_button_time,recall_button_time,learn_shortcut_time,recall_shortcut_time,"+
                 "learn_explainer_time,recall_explainer_time\n"
                 )
        df_writer = csv.writer(df, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open("site_info.csv", "r") as f:
            r = csv.DictReader(f)
            for row in r:
                # Format: URL, platform, [sitedata], [likerts], [timings]
                record = [
                    # Site info
                    row['URL'], row['Platform'],
                    # Convert colours to human names and group
                    #convert_rgb_to_names(row['Colour']),
                    #convert_rgb_to_names(row['Background Colour']),
                ]
                # For each property, make a boolean variable for each possible result
                for size in ['text', 'small', 'average', 'wide', 'long', 'large']:
                    record.append(size == row['Size'])
                for loc in ['top left', 'top', 'top right', 'left', 'content', 'right', 'bottom left', 'bottom',
                            'bottom right', 'dropdown', 'side menu']:
                    record.append(loc == row['Location'])
                for t in ['button', 'banner', 'image', 'menu item', 'text']:
                    record.append(t == row['Type'])
                # Already boolean
                record.append(row['Sticky?'])
                for v in ['Yes', 'Cookie Notice', 'No']:
                    record.append(v == row['Visible on load?'])
                # Make labelling boolean
                record.append(row['Label'] != '')
                # Clicks required is 1 or 2, so treat as boolean (is single click)
                record.append(row['Clicks Required'] == '1')

                # Compute average for each likert scale as value from -2 to 2
                likert_qs = ['button-discover','button-distinct','shortcut-discover','shortcut-intuitive',
                             'text-discover', 'text-comprehend', 'safety-discover']
                for l in likert_qs:
                    if (row['URL'], row['Platform']) in likerts:
                        n,v = 0, 0
                        for r in likerts[row['URL'], row['Platform']]:
                            if l in r:
                                v += likert_to_number(r[l])
                                n += 1
                        record.append(v / max(n, 1))
                    else:
                        record.append(0)
                # Compute average timings for site
                timing_qs = ['learn_button_time', 'recall_button_time', 'learn_shortcut_time', 'recall_shortcut_time',
                           'learn_explainer_time', 'recall_explainer_time']
                # Compute combined record for each site
                for t in timing_qs:
                    if (row['URL'], row['Platform']) in timings and t in timings[row['URL'], row['Platform']]:
                        record.append(timings[row['URL'], row['Platform']][t])
                    else:
                        record.append(0)
                # Save to file
                df_writer.writerow(record)

if __name__ == '__main__':
    combine_data()
    data = pd.read_csv("logistic_regression_info.csv")
    # Divide the data to training set and test set
    x_cols = [
        "Size_text","Size_small","Size_average","Size_wide","Size_long","Size_large",
        "Location_top_left","Location_top","Location_top_right","Location_left","Location_content","Location_right","Location_bottom_left","Location_bottom","Location_bottom_right","Location_menu", #,"Location_dropdown" - only 1 site
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
        if ycol == "button-distinct":
            x_cols.remove("Location_menu")
            x_cols.remove("Type_menu_item")
            x_cols.remove("Location_content")
            x_cols.remove("Size_large")
        elif ycol == "learn_button_time":
            x_cols.remove("Size_small")
            x_cols.remove("Location_bottom_left")
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

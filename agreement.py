# Imports
import csv

import sklearn.metrics
from sklearn.metrics import cohen_kappa_score
import numpy as np
from collections import Counter

def load_survey_data():
    # Load survey responses from file into a dictionary
    responses = {}
    with open('exit_button_annotations.csv', 'r') as annotations_file:
        reader = csv.DictReader(annotations_file)
        for row in reader:
            if row['StartDate'] == 'Start Date' or row['StartDate'][0] == '{':
                # Skip the labels row
                continue
            # Extract key fields
            site = row['eval-site']
            platform = row['eval-platform']
            # Delete unnecessary [qualtrics] fields
            del row['StartDate'], row['EndDate'], row['Status'], row['Progress'], \
                row['Duration (in seconds)'], row['Finished'], row['RecordedDate'], \
                row['ResponseId'], row['DistributionChannel'], row['UserLanguage'], \
                row['eval-site'], row['eval-platform'], row['button-comments'], \
                row['shortcut-comments'], row['text-comments'], row['safety-comments']
            if (site,platform) in responses:
                responses[(site,platform)].append(row)
            else:
                responses[site,platform] = [row]
    return responses

def agreements(responses):
    # For each survey likert scale, compute Fleiss' Kappa
    questions = ['button-discover','button-distinct','shortcut-discover','shortcut-intuitive',
                'text-discover', 'text-comprehend', 'safety-discover']

    # Matrix of responses per question where rows are evaluators and columns are site/platform pairs
    kappas = {q: {'Fleiss': 0, 'Cohen': 0} for q in questions}
    for question in questions:
        person_responses = {'Yanna':[], 'Alice':[], 'Kieron Ivy':[]}
        confusion_mat = []
        for site in responses:
            # FLEISS KAPPA IMPLEMENTATION
            if (any(1 for response in responses[site] if response['eval-name'] == 'Alice' and response[question] != '') and
                any(1 for response in responses[site] if response['eval-name'] == 'Kieron Ivy' and response[question] != '')):
                # FLEISS KAPPA IMPLEMENTATION
                filtered_responses = [d[question] for d in filter(
                    lambda r: question in r and r[question] != '' and r['eval-name'] != 'Yanna', responses[site])]
                counts = Counter(filtered_responses)
                options = ['Strongly disagree', 'Somewhat disagree', 'Neither agree nor disagree', 'Somewhat agree',
                           'Strongly agree']
                confusion_mat.append([counts[option] if option in counts else 0 for option in options])

                # COHENS KAPPA IMPLEMENTATION
                for response in responses[site]:
                    person_responses[response['eval-name']].append(response[question])
        # Fleiss' Kappa
        confusion_mat = np.array(confusion_mat)
        #print(question, '\n', confusion_mat)
        n_sites, _ = confusion_mat.shape
        n_annotators = 2

        p = np.sum(confusion_mat, axis=0) / (n_sites * n_annotators)
        pp = (np.sum(confusion_mat * confusion_mat, axis=1) - n_annotators) / (n_annotators * (n_annotators - 1))
        pbar = np.sum(pp) / n_sites
        pbar_e = np.sum(p * p)
        fleiss_kappa = (pbar - pbar_e) / (1 - pbar_e)
        cohen_kappa = sklearn.metrics.cohen_kappa_score(person_responses['Alice'], person_responses['Kieron Ivy'])

        kappas[question]['Fleiss'] = fleiss_kappa
        kappas[question]['Cohen'] = cohen_kappa
    return kappas


if __name__ == "__main__":
    responses = load_survey_data()
    kappas = agreements(responses)
    print(str(kappas).replace("},", "},\n"))


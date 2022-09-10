import csv
from collections import defaultdict
import numpy as np
from math import sqrt
import scipy.stats as stats
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from statsmodels.graphics.mosaicplot import mosaic

from evaluate import sitelist_filename

countries = ['UK', 'Ireland', 'Australia', 'New Zealand', 'USA', 'Canada']
categories = ['Domestic Abuse', 'Rape/SA', 'LGBTQ+', 'BAME(R)', 'Sobreity', 'Smoking', 'Gambling',
              'Family Planning', 'Parenting', 'Children', 'Homelessness', 'Sexual health', 'Mental Health',
              'Physical Health', 'Disability', 'Elderly', 'Past offenders', 'Victims', 'Police', 'Misc']
collapsed_categories = ['Gendered Violence', 'Minorities', 'Addiction', 'Families', 'Healthcare', 'Crime', 'Misc']
presence = ['Present', 'Absent']

def count_mechanisms(platform, mechanism, use_collapsed_categories=False):
    selected_categories = collapsed_categories if use_collapsed_categories else categories
    # Count times mechanism was present on platform
    country_counts = {(country,present): 0 for country in countries for present in presence}
    category_counts = {(category,present): 0 for category in selected_categories for present in presence}
    total = 0
    with open(sitelist_filename, "r") as f:
        reader = csv.DictReader(f)
        for site in reader:
            category = site['Category']
            # Collapse categories
            if use_collapsed_categories:
                if category in ['Domestic Abuse', 'Rape/SA']: category = 'Gendered Violence'
                elif category in ['LGBTQ+', 'BAME(R)']: category = 'Minorities'
                elif category in ['Sobreity', 'Smoking', 'Gambling']: category = 'Addiction'
                elif category in ['Family Planning', 'Parenting', 'Children']: category = 'Families'
                elif category in ['Sexual health', 'Mental Health', 'Physical Health', 'Disability']: category = 'Healthcare'
                elif category in ['Past offenders', 'Victims', 'Police']: category = 'Crime'
                else: category = 'Misc'
            else:
                if category not in categories:
                    category = 'Misc'

            country = site['Region']
            present = ((platform == 'Desktop' and mechanism == 'Button' and site['Desktop Exit Button?'] != '') or
                (platform == 'Desktop' and mechanism == 'Shortcut' and site['Keyboard shortcut type'] != '') or
                (platform == 'Mobile' and mechanism == 'Button' and site['Mobile Exit button?'] != '') or
                (platform == 'Mobile' and mechanism == 'Shortcut' and site['Mobile shortcut?'] != ''))
            country_counts[country,presence[1-present]]+=1
            category_counts[category,presence[1-present]]+=1
            if present:
                total += 1

    return country_counts, category_counts, total


def chi_squared_tests(platform, mechanism, use_collapsed_categories=False):
    selected_categories = collapsed_categories if use_collapsed_categories else categories
    country_counts, category_counts, total = count_mechanisms(platform, mechanism, use_collapsed_categories)
    residuals = {}
    likelihood_mechanism = total / 2045.0
    chi2_country = 0
    for i, country in enumerate(countries):
        # Entry for presence in country
        e_ij = likelihood_mechanism * (country_counts[country,'Present'] + country_counts[country,'Absent'])
        r_ij = float(country_counts[country,'Present'] - e_ij)/sqrt(e_ij) if e_ij != 0 else 0
        residuals[country,'Present'] = r_ij
        chi2_country += r_ij**2
        # Entry for absence in country
        e_ij = (1-likelihood_mechanism) * (country_counts[country,'Present'] + country_counts[country,'Absent'])
        r_ij = float(country_counts[country,'Absent'] - e_ij) / sqrt(e_ij) if e_ij != 0 else 0
        residuals[country,'Absent'] = r_ij
        chi2_country += r_ij ** 2
    dof = (len(countries) - 1) * (len(selected_categories) - 1)
    p_country = 1 - stats.chi2.cdf(chi2_country, dof)
    draw_mosaic(country_counts, residuals, platform, mechanism)

    chi2_category = 0
    for j, category in enumerate(selected_categories):
        # presence within category
        e_ij = likelihood_mechanism * (category_counts[category,'Present'] + category_counts[category,'Absent'])
        r_ij = float(category_counts[category,'Present'] - e_ij)/sqrt(e_ij) if e_ij != 0 else 0
        residuals[category,'Present'] = r_ij
        chi2_category += r_ij**2
        # absence within category
        e_ij = (1-likelihood_mechanism) * (category_counts[category,'Present'] + category_counts[category,'Absent'])
        r_ij = float(category_counts[category,'Absent'] - e_ij) / sqrt(e_ij) if e_ij != 0 else 0
        residuals[category,'Absent'] = r_ij
        chi2_category += r_ij ** 2
    p_category = 1 - stats.chi2.cdf(chi2_country, dof)
    draw_mosaic(category_counts, residuals, platform, mechanism)

    return chi2_country, chi2_category, dof, min(p_country, 1-p_country), min(p_category, 1-p_category)

def draw_mosaic(counts, residuals, platform, mechanism):
    # Set colour based on residuals
    props = lambda k: {'color': 'red' if residuals[k] > 4 else
                                'brown' if residuals[k] > 2 else
                                'saddlebrown' if residuals[k] > 0.5 else
                                'blue' if residuals[k] < -4 else
                                'teal' if residuals[k] < -2 else
                                'yellowgreen' if residuals[k] < -0.5 else
                                'green' # -0.5 <= r <= 0.5
    }
    # Provide same colours with labels for the legend
    legend_colours = [
        Patch(color='red', label='residual > 4'),
        Patch(color='brown', label='4 >= residual > 2'),
        Patch(color='saddlebrown', label='2 >= residual > .5'),
        Patch(color='green', label='0.5 >= residual >= -0.5'),
        Patch(color='yellowgreen', label='-0.5 > residual >= -2'),
        Patch(color='teal', label='-2 > residual >= -4'),
        Patch(color='blue', label='-4 > residual'),
    ]
    # Generate plot for this figure
    fig, ax = plt.subplots(figsize=(10,6))
    # Remove all labels
    labeliser = lambda k: '' #"\n".join(k) if abs(residuals[k])>4 else ''
    # Generate a mosaic plot based on counts with colours given by associated residuals
    mosaic(counts, ax=ax, gap=0.01, labelizer=labeliser, properties=props,
           title='Presence of '+platform+' '+mechanism)
    # Fix x labels
    plt.setp(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
    # Add legend
    fig.legend(handles=legend_colours, loc=(0.725, 0.5))
    # Fix spacing
    fig.subplots_adjust(left=0.1, right=0.7, bottom=0.2)
    fig.show()

if __name__ == '__main__':
    print(chi_squared_tests('Desktop', 'Button'))
    #print(chi_squared_tests('Desktop', 'Shortcut'))
    print(chi_squared_tests('Mobile', 'Button'))
    #print(chi_squared_tests('Mobile', 'Shortcut'))
    print(chi_squared_tests('Desktop', 'Button', True))
    #print(chi_squared_tests('Desktop', 'Shortcut', True))
    print(chi_squared_tests('Mobile', 'Button', True))
    #print(chi_squared_tests('Mobile', 'Shortcut', True))
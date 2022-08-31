import csv
from collections import defaultdict
import numpy as np
from math import sqrt
import scipy.stats as stats
import matplotlib.pyplot as plt
from statsmodels.graphics.mosaicplot import mosaic

from evaluate import sitelist_filename

countries = ['UK', 'Ireland', 'Australia', 'New Zealand', 'USA', 'Canada']
categories = ['Domestic Abuse', 'Rape/SA', 'LGBTQ+', 'BAME(R)', 'Sobreity', 'Smoking', 'Gambling',
              'Family Planning', 'Parenting', 'Children', 'Homelessness', 'Sexual health', 'Mental Health',
              'Physical Health', 'Disability', 'Elderly', 'Past offenders', 'Victims', 'Police', 'Misc']
collapsed_categories = ['Gendered Violence', 'Minorities', 'Addiction', 'Families', 'Healthcare', 'Crime', 'Misc']

def count_mechanisms(platform, mechanism, use_collapsed_categories=False):
    selected_categories = collapsed_categories if use_collapsed_categories else categories
    # Count times mechanism was present on platform
    nsites = {(country, category): 0 for country in countries for category in selected_categories}
    counts = {(country, category): 0 for country in countries for category in selected_categories}
    country_counts = {country: 0 for country in countries}
    category_counts = {category: 0 for category in selected_categories}
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
            nsites[(country,category)]+=1
            if ((platform == 'Desktop' and mechanism == 'Button' and site['Desktop Exit Button?'] != '') or
                (platform == 'Desktop' and mechanism == 'Shortcut' and site['Keyboard shortcut type'] != '') or
                (platform == 'Mobile' and mechanism == 'Button' and site['Mobile Exit button?'] != '') or
                (platform == 'Mobile' and mechanism == 'Shortcut' and site['Mobile shortcut?'] != '')):
                    country_counts[country]+=1; category_counts[category]+=1; counts[(country, category)]+=1; total += 1

    return counts, country_counts, category_counts, nsites, total


def chi_squared_test(platform, mechanism, use_collapsed_categories=False):
    selected_categories = collapsed_categories if use_collapsed_categories else categories
    counts, country_counts, category_counts, nsites, total = count_mechanisms(platform, mechanism, use_collapsed_categories)
    residuals = {}
    likelihood_mechanism = total / 2045.0
    chi2 = 0
    for i, country in enumerate(countries):
        for j, category in enumerate(selected_categories):
            e_ij = likelihood_mechanism * nsites[(country,category)] # float(country_counts[country] * category_counts[category]) / float(total)
            r_ij = float(counts[(country,category)] - e_ij)/sqrt(e_ij) if e_ij != 0 else 0
            residuals[(country, category)] = r_ij
            chi2 += r_ij**2
    dof = (len(countries) - 1) * (len(selected_categories) - 1)
    p = 1 - stats.chi2.cdf(chi2, dof)
    draw_mosaic(counts, residuals, platform, mechanism)
    return chi2, dof, p

def draw_mosaic(counts, residuals, platform, mechanism):
    # TODO derive thresholds based on p values of residuals
    props = lambda k: {'color': 'red' if residuals[k] > 4 else
                                'orange' if residuals[k] > 2 else
                                'yellow' if residuals[k] > 0.5 else
                                'light blue' if residuals[k] < -4 else
                                'blue' if residuals[k] < -2 else
                                'darkblue' if residuals[k] < -0.5 else
                                'grey'
                       }
    labeliser = lambda k: "\n".join(k) if abs(residuals[k])>4 else ''
    mosaic(counts, gap=0.01, properties=props, labelizer=labeliser, title='Presence of '+platform+' '+mechanism)
    plt.show()

if __name__ == '__main__':
    print(chi_squared_test('Desktop', 'Button'))
    #print(chi_squared_test('Desktop', 'Shortcut'))
    print(chi_squared_test('Mobile', 'Button'))
    #print(chi_squared_test('Mobile', 'Shortcut'))
    print(chi_squared_test('Desktop', 'Button', True))
    #print(chi_squared_test('Desktop', 'Shortcut', True))
    print(chi_squared_test('Mobile', 'Button', True))
    #print(chi_squared_test('Mobile', 'Shortcut', True))
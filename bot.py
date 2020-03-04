#!/usr/bin/env python3

import collections
import google_streetview.api
import locale
import os
import random
import pandas
import time

try:
    locale.setlocale(locale.LC_ALL, "en_US")
except:
    locale.setlocale(locale.LC_ALL, "en_US.utf8")

# Time to wait between crash and reboot of the bot
REBOOT_TIME = 60

# Tweepy API config
TWEEPY_RETRY_CONFIG = {
    "retry_count": 5,
    "retry_delay": 5,
    "retry_errors": set([
        503, # over capacity
    ])
}

# Directory to save Google Street View images and metadata files to
IMAGES_DIR = "."
DEFAULT_IMAGE_PATH = "%s/gsv_0.jpg" % IMAGES_DIR

# The CSV file to retrieve data from
INPUT_PARCELS = "./parcels_shuffled_2020_03_02.csv"
INPUT_NEIGHBORHOODS = "./neighborhoods.csv"
INPUT_TRACTS = "./tracts.csv"
INPUT_BLOCKGROUPS = "./blockgroups.csv"

TRACT_ATTRIBUTES = pandas.read_csv(INPUT_TRACTS)
NEIGHBORHOOD_ATTRIBUTES = pandas.read_csv(INPUT_NEIGHBORHOODS)
BLOCKGROUP_ATTRIBUTES = pandas.read_csv(INPUT_BLOCKGROUPS)

# Pregenerated images
NEIGHBORHOOD_IMAGES = "./neighborhood_maps/"
PARCEL_IMAGES = "./composite/"
TRACT_AGE_GRAPHS = "./tract_age_graphs/"
TRACT_ETH_HET_MAPS = "./tract_eth_het_maps/"
TRACT_RENT_MAPS = "./tract_rent_maps/"

# The JSON file where credentials are stored
CREDENTIALS_FILE = "credentials.json"

# File to persist the bot's current place in the input CSV file
STATUS_FILE = "last_idx.txt"

# Miscellaneous constants
VOWELS = "AEIOUaeiou"
DIGITS = "1234567890"

# Time to sleep between new tweets
#SLEEP_TIME = 30 * 60 # 30 minutes
SLEEP_TIME = 60 * 60 # 1 hour

# If less than this many miles, convert to feet
MILES_FEET_CUTOFF = 0.1

# Conversion factors
METERS_IN_MILE = 1609.344
FEET_IN_MILE = 5280

# Dicts to map values as they appear in the CSV file to values as they should
# appear in tweets. The names of the constants roughly follows the format of
# {column name}_MAPPING except where the column name would be unreadable in all
# caps
R_BLDG_STYL_MAPPING = collections.defaultdict(
    lambda: "residential parcel", # default value
    {
        "BL": "Bi-Level",
        "BW": "Bungalow",
        "CL": "Colonial",
        #"CN": "Contemporary",
        "CP": "Cape-style House",
        #"CV": "Conventional",
        "DK": "Triple Decker",
        "DX": "Duplex",
        #"OT": "Other",
        "RE": "Row House",
        "RM": "Row House",
        "RN": "Ranch",
        "RR": "Raised Ranch",
        "SL": "Split Level",
        "TF": "Two-Family Stack",
        "TD": "Tudor",
        "TL": "Tri-Level",
        "SD": "Semidetached",
        "VT": "Victorian"
    }
)
LU_MAPPING = {
    # A, R1, R2, R3, R4, RL = residential parcel
    # CC, CD, CM = condominium
    "AH": "agricultural parcel",
    "C": "commercial parcel",
    "CL": "commercial parcel", # "commercial land"
    "CP": "parking lot",
    "E": "tax exempt parcel",
    "EA": "tax exempt parcel",
    "I": "industrial parcel",
    "RC": "mixed-use parcel"
}
PERMIT_TYPE_MAPPING = {
    "Short Form Bldg Permit": "short form permit for building renovation",
    "Electrical Permit": "permit for electrical work",
    "Plumbing Permit": "permit for a plumbing work",
    "Gas Permit": "gas permit",
    "Electrical Low Voltage": "permit for electrical work",
    "Certificate of Occupancy": "permit for certificate of occupancy",
    "Long Form/Alteration Permit": "long form permit for alteration",
    "Excavation Permit": "permit for excavation",
    "Electrical Fire Alarms": "permit for fire alarm work",
    "Electrical Temporary Service": "permit for electrical work",
    "Use of Premises": "use of premises permit",
    "Amendment to a Long Form": "amendment to a long form permit",
    "Erect/New Construction": "permit for new construction",
    "Foundation Permit": "foundation permit"
}
ST_NAME_SUF_MAPPING = {
    "AL": "Alley",
    "AV": "Ave.",
    "BL": "Blvd.",
    "CC": "Circuit",
    "CI": "Cir.",
    "CR": "Crescent",
    "CW": "Crossway",
    "DR": "Drive",
    "EXD": "Ext.",
    "HW": "Hwy.",
    "LA": "Ln.",
    "MA": "Mall",
    "PA": "Path",
    "PK": "Park",
    "PW": "Pkwy.",
    "PZ": "Plaza",
    "RO": "Row",
    "TE": "Ter.",
    "WA": "Way",
    "WH": "Wharf",
    "WY": "Way",
    "XT": "Ext."
}
NEIGHBOURHOOD_HASHTAG_MAPPING = {
    "East Boston": "#eastie",
    "South Boston": "#southie",
    "South Boston Waterfront": "#seaport"
}

# Special: A "the" is prepended to these neighbourhood values
# e.g. "South End" -> "the South End"
NEIGHBOURHOOD_PREPEND_THE = {
    "South End",
    "North End",
    "West End",
    "South Boston Waterfront",
    "Leather District"
}

# determine whether or not to skip a row in the data
def skip_row(row):
    if (pandas.isnull(row["ST_NUM"])):
        return "no ST_NUM"
    return False

def human_readable_distance(distance_meters):
    distance_miles = distance_meters / METERS_IN_MILE
    if (distance_miles < MILES_FEET_CUTOFF):
        return "%d feet" % (distance_miles * FEET_IN_MILE)
    else:
        return "%0.2f miles" % distance_miles

# Convert a neighbourhood into a hashtag
def neighbourhood_to_hashtag(neighbourhood_name):
    if (neighbourhood_name in NEIGHBOURHOOD_HASHTAG_MAPPING):
        return NEIGHBOURHOOD_HASHTAG_MAPPING[neighbourhood_name]
    else:
        return "#%s" % neighbourhood_name.lower().replace(" ", "")

# Return the proper article based on whether or not the first character of a
# string is a vowel or not
def article_for(str_):
    if (str_[0] in VOWELS):
        return "an"
    else:
        return "a"

# Returns True if a string contains digits; False otherwise
def contains_digits(str_):
    if ((type(str_) is float) or (type(str_) is int)):
        return True
    else:
        for digit in DIGITS:
            if (digit in str_):
                return True

# Given an address and lon-lat pair, download the address's Google Street View
# image, falling back to the lon-lat pair if the address has no street number
def pull_picture(address, lon, lat, api_key):
    if (address[0] in DIGITS):
        address = "%s, Boston" % address
    else:
        address = "%d,%d" % (lat, lon)
    results = google_streetview.api\
        .results([{
            "size": "1200x675",
            "location": address,
            "key": api_key
        }])\
        .download_links(IMAGES_DIR)

# Given a string of words, individually capitalize each word
def capitalize_all_words(str_):
    return " ".join([
        word.capitalize()
        for word in str_.split(" ")
    ])

# Given a row of data from the parcels CSV file, generate a tweet describing
# its attributes, download an image from Google Street View, and return the
# content of that tweet.
def generate_parcel_tweet(row, googlemaps_api_key):

    ### Address string: "This parcel on Waymount St." or "72 Day St."

    if (pandas.isnull(row["ST_NUM"])):
        street_num = "This parcel on"
    else:
        street_num = str(row["ST_NUM"])

    suffix_raw = row["ST_NAME_SUF"]
    if (suffix_raw in ST_NAME_SUF_MAPPING):
        suffix = ST_NAME_SUF_MAPPING[suffix_raw]
    else:
        if (not pandas.isnull(suffix_raw)):
            suffix = suffix_raw.capitalize() + "."
        else:
            suffix = None

    if (suffix):
        address = " ".join([
            street_num, capitalize_all_words(row["ST_NAME"]), suffix
        ])
    else:
        address = " ".join([
            street_num, capitalize_all_words(row["ST_NAME"])
        ])

    ### Building style: "residential brownstone"
    if (row["LU"] in LU_MAPPING):
        building_style = LU_MAPPING[row["LU"]]
    else:
        building_style = R_BLDG_STYL_MAPPING[row["R_BLDG_STYL"]]

    ### Year built
    year = row["YR_BUILT"]
    if (pandas.isnull(year)):
        built_in_year = ""
    else:
        built_in_year = " built in %d" % year

    ### Neighbourhood / section: x section of y
    # We manipulate a list here instead of using string manipulations because
    # several synonyms for a neighbourhood are separated by slashes, and it's
    # easier to do comparisons and modifications on a list of these synonyms
    neighbourhood = row["neighborhood"]
    if (row["section"] == "Cleveland Circle (/Brighton)"):
        sections = ["Cleveland Circle", "Brighton"] # Special case
    else:
        sections = row["section"].split("/")

    # "South End" -> "the South End"
    if (neighbourhood in NEIGHBOURHOOD_PREPEND_THE):
        neighbourhood_fixed = "the %s" % neighbourhood_to_hashtag(neighbourhood)
    else:
        neighbourhood_fixed = neighbourhood_to_hashtag(neighbourhood)

    # "Fenway/West Fens section of Fenway" -> "West Fens section of Fenway"
    try:
        sections.remove(neighbourhood)
    except ValueError:
        pass

    # "in the Charlestown section of Charlestown" -> "in Charlestown"
    if ((len(sections) == 0) or ("Unnamed" in sections)):
        neighbourhood_str = "in %s" % neighbourhood_fixed
    else:
        neighbourhood_str = "in the %s section of %s" % (
            "/".join(sections), neighbourhood_fixed
        )

    ### Assessed value
    assessed_value = "{:,}".format(row["AV_TOTAL"])

    ### Renovations
    year_renovated = row["ISSUED_DATE"]
    if (pandas.isnull(year_renovated)):
        renovated_str = "No building permits were issued for this address since 2006"
    else:
        renovated_str = "A %s was last issued in %d" % (
            PERMIT_TYPE_MAPPING[row["permittypedescr"]], year_renovated
        )

    ### Download picture
    pull_picture(
        "%s, %s" % (address, neighbourhood_fixed),
        row["x"], row["y"],
        googlemaps_api_key
    )

    return (
        f"{address} is {article_for(building_style)} {building_style}{built_in_year} {neighbourhood_str}."
        f" The current value in the Boston tax assessment database is ${assessed_value}."
        f" {renovated_str}."
    )

# Given a row of data from the parcels CSV file, generate a tweet describing
# the attributes of the neighbourhood and return relevant images
def generate_neighborhood_tweet(row):
    neighborhood_name = row["neighborhood"]

    # neighborhood attributes are stored in a separate file
    neighborhood_attributes = NEIGHBORHOOD_ATTRIBUTES[
        NEIGHBORHOOD_ATTRIBUTES["Name"] == neighborhood_name
    ].iloc[0]
    n_transit_lines = neighborhood_attributes["n_bus_lines"] + neighborhood_attributes["n_subway_lines"]

    # also block group attributes
    blockgroup_attributes = BLOCKGROUP_ATTRIBUTES[
        BLOCKGROUP_ATTRIBUTES["BG_ID_10"] == row["BG_ID_10"]
    ].iloc[0]
    distance = human_readable_distance(blockgroup_attributes["MEDIAN_TRANSIT_METERS"])

    # closest stop info
    stop_type = row["STOP_TYPE"].lower()
    stop_name = row["STOP_NAME"]
    time = "%0.2f" % (row["NEAREST_TRANSIT_SECONDS"] / 60)

    # neighborhood image always exists
    neighborhood_image = "%s/%s.png" % (
        NEIGHBORHOOD_IMAGES, neighborhood_name.lower().replace(" ", "_")
    )

    # parcel image always may not
    parcel_image = "%s/%d.jpg" % (
        PARCEL_IMAGES, row["Land_Parcel_ID"]
    )
    if (os.path.isfile(parcel_image)):
        images = [neighborhood_image, parcel_image]
    else:
        images = [neighborhood_image, parcel_image]

    return {
        "message": (
            f"The closest MBTA {stop_type} stop is {stop_name}."
            f" This is a {time} minute walk, according to OpenStreetMap."
            f" The average walking distance to a transit stop in this census block group is {distance}."
            f" {n_transit_lines} different transit lines serve {neighborhood_name}."
        ),
        "images": images
    }

# The density in this census tract (*123) is 13,234 people/square mile, which is less dense than 75% of Boston. 22% of people rent their home, with a median rent of $2,400 (12% higher than the citywide median).
# Chloropleth ofmedian rent, red outline of the tract in question, white to green colormap
def generate_tract_housing_characteristics_tweet(row):
    tract_id = int(row["CT_ID_10"])
    tract_attributes = TRACT_ATTRIBUTES[
        TRACT_ATTRIBUTES["CT_ID_10"] == row["CT_ID_10"]
    ].iloc[0]

    population_density = locale.format("%d", int(tract_attributes["PopDen"]), grouping = True)
    population_density_pctile = int(tract_attributes["PopDenPctile"] * 100)

    percent_renters = int(tract_attributes["RentersPer"] * 100)

    median_rent = locale.format("%d", int(tract_attributes["MedGrossRent"]), grouping = True)
    median_rent_pctile = int(tract_attributes["MedGrossRentPctile"] * 100)

    tract_rent_map = "%s/%d.png" % (TRACT_RENT_MAPS, tract_id)

    return {
        "message": (
            f"The density in this census tract ({tract_id}) is {population_density} per square mile, which is less than {population_density_pctile}% of Boston."
            f" {percent_renters}% of people rent their home, with a median rent of ${median_rent} ({median_rent_pctile}% higher than the neighborhood-level median rent)."
        ),
        "images": [tract_rent_map]
    }

# This census tract (*123) is 19% more racially/ethnically diverse than the city average.
# Chloropleth of ethnic heterogeneity, red outline of the tract in question, viridis colormap
def generate_tract_ethnic_heterogeneity_tweet(row):
    tract_id = int(row["CT_ID_10"])
    tract_attributes = TRACT_ATTRIBUTES[
        TRACT_ATTRIBUTES["CT_ID_10"] == row["CT_ID_10"]
    ].iloc[0]

    eth_het_pctile = tract_attributes["EthHetPctile"]

    if (eth_het_pctile > 0.5):
        more_less = "more"
        eth_het_ratio = eth_het_pctile - 0.5
    else:
        more_less = "less"
        eth_het_ratio = 0.5 - eth_het_pctile
    eth_het_ratio = int(eth_het_ratio * 100)

    tract_eth_het_map = "%s/%d.png" % (TRACT_ETH_HET_MAPS, tract_id)

    return {
        "message": (
            f"This census tract ({tract_id}) is {eth_het_ratio}% {more_less} racially/ethnically diverse than the city average."
        ),
        "images": [tract_eth_het_map]
    }

# In this census tract ($123), 20% of residents have a high school degree or less, 20% have completed some college or a bachelor’s degree, and 20% have a graduate degree.
# Image: bar graph of ages
def generate_tract_education_age_tweet(row):
    tract_id = int(row["CT_ID_10"])
    tract_attributes = TRACT_ATTRIBUTES[
        TRACT_ATTRIBUTES["CT_ID_10"] == row["CT_ID_10"]
    ].iloc[0]

    percent_hs = int(tract_attributes["highSchoolDegreeOrless"])
    percent_coll = int(tract_attributes["completedCollegeOrBachelorDegree"])
    percent_grad = int(tract_attributes["graduateDegree"])

    tract_age_graph = "%s/%d.png" % (TRACT_AGE_GRAPHS, tract_id)

    return {
        "message": (
            f"In this census tract ({tract_id}),"
            f" {percent_hs}% of residents have a high school degree or less,"
            f" {percent_coll}% have completed some college or a bachelor's degree,"
            f" and {percent_grad}% have a graduate degree."
        ),
        "images": [tract_age_graph]
    }

if (__name__ == "__main__"):
    import argparse
    import json
    import slack
    import traceback
    import tweepy

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--dry-run", dest = "dry_run", action = "store_true", default = False)
    args = parser.parse_args()

    print("loading")

    with open(CREDENTIALS_FILE, "r") as f:
        credentials = json.load(f)

    auth = tweepy.OAuthHandler(
        credentials["twitter"]["consumer_key"],
        credentials["twitter"]["consumer_secret"]
    )
    auth.set_access_token(
        credentials["twitter"]["access_token"],
        credentials["twitter"]["access_token_secret"]
    )
    api = tweepy.API(auth)

    slack_client = slack.WebClient(token = credentials["slack"]["token"])

    # wrapper around tweet functionality
    def tweet(message, image_paths = [], reply_to_status = None):
        tweet_kwargs = {}

        print("")

        # upload images
        if (len(image_paths) > 0):
            media_ids = []
            for image_path in image_paths:
                if (args.dry_run):
                    print("Not uploading: %s" % image_path)
                else:
                    print("Uploading: %s" % image_path)
                    media_ids.append(api.media_upload(image_path).media_id)
            tweet_kwargs["media_ids"] = media_ids

        # reply
        if (reply_to_status):
            tweet_kwargs["in_reply_to_status_id"] = reply_to_status.id
            message = "@bariexplorer %s" % message
            print("Set in_reply_to_status_id to %d" % reply_to_status.id)

        if (args.dry_run):
            print("Not tweeting: %s" % message)
        else:
            print("Tweeting: %s" % message)
            return api.update_status(message, **tweet_kwargs)

    df = pandas.read_csv(INPUT_PARCELS)
    start_at = 0

    # Load the previous position of the bot
    if (os.path.isfile(STATUS_FILE)):
        with open(STATUS_FILE, "r") as f:
            start_at = int(f.read())

    # Loop over rows
    for (index, row) in df[start_at + 2:].iterrows():
        try:
            skip = skip_row(row)
            if (skip):
                if (type(skip) is str):
                    print("Skipping row, reason: %s" % skip)
            else:
                print("Gathering information for row: %d" % index)
                main_status = None

                # Save position
                with open(STATUS_FILE, "w") as f:
                    f.write(str(index))

                ################################################################
                # Main tweet ###################################################

                main_message = generate_parcel_tweet(row, credentials["googlemaps"])

                if (os.path.isfile(DEFAULT_IMAGE_PATH)):
                    main_tweet_images = [DEFAULT_IMAGE_PATH]
                else:
                    main_tweet_images = None
                    main_message = "%s There is no image available for this parcel." % main_message

                main_status = tweet(
                    message = "%s (1/2)" % main_message,
                    image_paths = main_tweet_images
                )

                try:
                    os.remove(DEFAULT_IMAGE_PATH)
                except:
                    pass

                ################################################################
                # Reply tweet (randomly chosen) ################################

                # each item in this list is a function that takes a row of input
                # and returns a dict with the keys "message" and "images",
                # containing the tweet text and the paths to images to use,
                # respectively.
                tweet_generators = [
                    #generate_neighborhood_tweet,
                    generate_tract_housing_characteristics_tweet,
                    #generate_tract_ethnic_heterogeneity_tweet,
                    #generate_tract_education_age_tweet,
                ]

                tweet_generator = random.choice(tweet_generators)
                print("\nCreating reply tweet using tweet generator:")
                print(tweet_generator)
                reply = tweet_generator(row)

                tweet(
                    message = "%s (2/2)" % reply["message"],
                    image_paths = reply["images"],
                    reply_to_status = main_status
                )

                time.sleep(SLEEP_TIME)
        except KeyboardInterrupt:
            raise
        except Exception as error:
            traceback.print_exc()
            slack_client.files_upload(
                channels = credentials["slack"]["channel"],
                initial_comment = "bariexplorer crashed! Stack trace attached. I will be restarting the bot in %d seconds 👍" % REBOOT_TIME,
                content = traceback.format_exc()
            )
            time.sleep(REBOOT_TIME)

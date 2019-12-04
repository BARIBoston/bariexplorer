Next release
* [x] Use hashtags for the neighbourhoods 
* [x] Reply tweet
  * [x] Parcel info
  * [x] Parcel map
    * [x] Satellite map
    * [x] Parcel outline
    * [x] Subway and bus icons
    * [x] <s>Road segment line</s> Determined to not be useful
* [x] Fix parcel values
  * [x] <s>Aggregate AV_TOTAL by grouping by Land_Parcel_ID and summing</s> the value for AV_TOTAL for records with the same Land_Parcel_ID are the same in the new file
  * [x] One tweet per parcel: either the zero value record or the first record observed

Future releases
* [ ] Reply tweet language: "The closest MBTA [bus/subway] stop is [stop_name]. This is a [time] minute walk, according to OpenStreetMap. The average walking distance to a transit stop in this census block group is [dist]. [Number] different transit lines serve [neighborhood_name]."

Images:
* [x] Parcel-level, with parcel outlined, walking directions traced, and stop indicated with yellow bus or white T icon
* [x] <s>Block group level, with same annotation as above</s>
* [x] Neighborhood level, with bus lines in yellow, T lines in their individual colors, and T stops indicated with white T icon

Variables:
* [x] For each stop: bus or subway
* [x] For each parcel: walking time to nearest stop
* [ ] For block group: average distance (in miles) to nearest transit stop
* [ ] For neighborhood: number of transit lines (bus + T) that are found in that neighborhood


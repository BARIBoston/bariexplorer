Next release
* [x] Use hashtags for the neighbourhoods 
* [ ] Reply tweet
  * [ ] Parcel info
  * [ ] Parcel map
    * [x] Satellite map
    * [x] Parcel outline
    * [ ] Subway and bus icons
    * [ ] Road segment line
* [ ] Fix parcel values
  * [ ] Aggregate AV_TOTAL by grouping by Land_Parcel_ID and summing

Future releases
Reply tweet language:
"The closest MBTA [bus/subway] stop is [stop_name]. This is a [time] minute walk, according to OpenStreetMap. The average walking distance to a transit stop in this census block group is [dist]. [Number] different transit lines serve [neighborhood_name]."

Images:
* [ ] Parcel-level, with parcel outlined, walking directions traced, and stop indicated with yellow bus or white T icon
* [ ] Block group level, with same annotation as above
* [ ] Neighborhood level, with bus lines in yellow, T lines in their individual colors, and T stops indicated with white T icon

Variables:
* [ ] For each stop: bus or subway
* [ ] For each parcel: walking time to nearest stop
* [ ] For block group: average distance (in miles) to nearest transit stop
* [ ] For neighborhood: number of transit lines (bus + T) that are found in that neighborhood


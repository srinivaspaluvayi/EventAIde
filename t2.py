event_details = [
        {
            "city":"new york",
            "events":[
                {
                    "event":"soccer match",
                    "date":"08/07/2025"
                }
            ]
        },
        {
        "city":"saint louis",
            "events":[
                {
                    "event":"baseball match",
                    "date":"08/07/2025"
                }
            ]
        }
    ]
def get_events_info_from_city(city):
    city = city.lower()
    events = [x["events"] for x in event_details if x["city"]==city]
    return events[0] if len(events)>0 else []
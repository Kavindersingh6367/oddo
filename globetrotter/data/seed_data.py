# -*- coding: utf-8 -*-
"""
Rich destination and activity seed data for GlobeTrotter platform.
"""

DESTINATIONS_DATA = [
    {
        "name": "Delhi",
        "country": "India",
        "region": "asia",
        "description": "India's vibrant capital, rich in Mughal heritage, grand colonial boulevards, and legendary street food.",
        "cost_index": 2,
        "popularity": 92,
        "recommended_duration_days": 3,
        "cover_image": "https://images.unsplash.com/photo-1587474260584-136574528ed5?auto=format&fit=crop&w=1200&q=80",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "travel_styles": "culture,food,budget,family",
        "activities": [
            {
                "name": "Red Fort & Old Delhi Heritage Walk",
                "description": "Explore the iconic 17th-century Mughal fortress and winding lanes of Shahjahanabad.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 650.0,
                "popularity": 95,
                "image": "https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80",
                "location_name": "Old Delhi"
            },
            {
                "name": "Chandni Chowk Street Food Feast",
                "description": "Sample mouthwatering paranthas, jalebis, chaat, and spiced kebabs from century-old stalls.",
                "category": "food",
                "duration_hours": 2.5,
                "estimated_cost": 850.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80",
                "location_name": "Chandni Chowk"
            },
            {
                "name": "Qutub Minar & Mehrauli Archaeological Park",
                "description": "Marvel at the world's tallest brick minaret and ancient Indo-Islamic monuments.",
                "category": "sightseeing",
                "duration_hours": 2.5,
                "estimated_cost": 600.0,
                "popularity": 90,
                "image": "https://images.unsplash.com/photo-1545128485-c400e7702796?auto=format&fit=crop&w=800&q=80",
                "location_name": "Mehrauli"
            },
            {
                "name": "Humayun's Tomb Garden Complex",
                "description": "Stroll through the UNESCO World Heritage charbagh garden tomb that inspired the Taj Mahal.",
                "category": "culture",
                "duration_hours": 2.0,
                "estimated_cost": 550.0,
                "popularity": 92,
                "image": "https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80",
                "location_name": "Nizamuddin East"
            },
            {
                "name": "India Gate & Kartavya Path Sunset Promenade",
                "description": "Witness the illuminated war memorial and lively evening atmosphere at the central avenue.",
                "category": "sightseeing",
                "duration_hours": 1.5,
                "estimated_cost": 0.0,
                "popularity": 94,
                "image": "https://images.unsplash.com/photo-1587474260584-136574528ed5?auto=format&fit=crop&w=800&q=80",
                "location_name": "Central Secretariat"
            }
        ]
    },
    {
        "name": "Jaipur",
        "country": "India",
        "region": "asia",
        "description": "The Pink City of royal Rajasthan, famed for majestic hilltop forts, vibrant bazaars, and regal palaces.",
        "cost_index": 2,
        "popularity": 95,
        "recommended_duration_days": 3,
        "cover_image": "https://images.unsplash.com/photo-1603288967969-952467d027f6?auto=format&fit=crop&w=1200&q=80",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "travel_styles": "culture,adventure,shopping,balanced",
        "activities": [
            {
                "name": "Amber Fort & Sheesh Mahal Exploration",
                "description": "Discover opulent Rajput architecture, the mirror palace, and panoramic Aravalli mountain views.",
                "category": "sightseeing",
                "duration_hours": 3.5,
                "estimated_cost": 750.0,
                "popularity": 98,
                "image": "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=800&q=80",
                "location_name": "Amer"
            },
            {
                "name": "City Palace & Jantar Mantar Observatory",
                "description": "Tour the active royal residence museum and world's largest stone astronomical observatory.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 900.0,
                "popularity": 94,
                "image": "https://images.unsplash.com/photo-1603288967969-952467d027f6?auto=format&fit=crop&w=800&q=80",
                "location_name": "Old City"
            },
            {
                "name": "Hawa Mahal (Palace of Winds) Photo Stop & Cafe",
                "description": "Admire the 953 honeycombed windows while enjoying masala chai with direct facade views.",
                "category": "sightseeing",
                "duration_hours": 1.5,
                "estimated_cost": 350.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=800&q=80",
                "location_name": "Badi Choupad"
            },
            {
                "name": "Nahargarh Fort Sunset & Padao Lounge",
                "description": "Catch breathtaking golden hour views over Jaipur city from the ridge of the fort.",
                "category": "nature",
                "duration_hours": 2.5,
                "estimated_cost": 500.0,
                "popularity": 93,
                "image": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=800&q=80",
                "location_name": "Nahargarh Hills"
            },
            {
                "name": "Chokhi Dhani Rajasthani Village & Thali Feast",
                "description": "Immersive cultural village fair with folk dancers, puppet shows, camel rides, and authentic feast.",
                "category": "food",
                "duration_hours": 4.0,
                "estimated_cost": 1400.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1613588796590-7cbbcb3cb678?auto=format&fit=crop&w=800&q=80",
                "location_name": "Tonk Road"
            }
        ]
    },
    {
        "name": "Udaipur",
        "country": "India",
        "region": "asia",
        "description": "The City of Lakes and Venice of the East, romantic palaces floating on glistening turquoise waters.",
        "cost_index": 3,
        "popularity": 93,
        "recommended_duration_days": 2,
        "cover_image": "https://images.unsplash.com/photo-1595658658481-d53d3f999875?auto=format&fit=crop&w=1200&q=80",
        "latitude": 24.5854,
        "longitude": 73.7125,
        "travel_styles": "relaxed,culture,luxury,solo",
        "activities": [
            {
                "name": "City Palace Udaipur & Museum Tour",
                "description": "Grand palace complex overlooking Lake Pichola featuring peacock courtyards and crystal galleries.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 850.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1595658658481-d53d3f999875?auto=format&fit=crop&w=800&q=80",
                "location_name": "Lake Pichola Bank"
            },
            {
                "name": "Lake Pichola Sunset Boat Cruise to Jag Mandir",
                "description": "Serene boat ride across tranquil waters with stops at the island palace of Jag Mandir.",
                "category": "relaxation",
                "duration_hours": 2.0,
                "estimated_cost": 950.0,
                "popularity": 98,
                "image": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=800&q=80",
                "location_name": "Rameshwar Ghat"
            },
            {
                "name": "Bagore Ki Haveli Folk Dance & Puppet Show",
                "description": "Mesmerizing evening Dharohar dance performances inside an 18th-century waterfront mansion.",
                "category": "entertainment",
                "duration_hours": 2.0,
                "estimated_cost": 400.0,
                "popularity": 91,
                "image": "https://images.unsplash.com/photo-1613588796590-7cbbcb3cb678?auto=format&fit=crop&w=800&q=80",
                "location_name": "Gangaur Ghat"
            },
            {
                "name": "Saheliyon Ki Bari Royal Garden Stroll",
                "description": "Lush historic garden with marble elephants, lotus pools, and gravity-fed fountains.",
                "category": "nature",
                "duration_hours": 1.5,
                "estimated_cost": 250.0,
                "popularity": 88,
                "image": "https://images.unsplash.com/photo-1545128485-c400e7702796?auto=format&fit=crop&w=800&q=80",
                "location_name": "Fateh Sagar"
            }
        ]
    },
    {
        "name": "Mumbai",
        "country": "India",
        "region": "asia",
        "description": "The City of Dreams, maximum city of finance, Bollywood, Victorian Gothic architecture, and coastal seascapes.",
        "cost_index": 3,
        "popularity": 91,
        "recommended_duration_days": 3,
        "cover_image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=1200&q=80",
        "latitude": 18.9220,
        "longitude": 72.8347,
        "travel_styles": "culture,food,business,adventure",
        "activities": [
            {
                "name": "Gateway of India & Colaba Heritage Walk",
                "description": "Iconic basalt archway, Taj Mahal Palace Hotel views, and colonial heritage quarters.",
                "category": "sightseeing",
                "duration_hours": 2.5,
                "estimated_cost": 300.0,
                "popularity": 95,
                "image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?auto=format&fit=crop&w=800&q=80",
                "location_name": "Apollo Bunder"
            },
            {
                "name": "Elephanta Caves UNESCO Island Excursion",
                "description": "Ferry voyage across Mumbai harbor to rock-cut cave temples dedicated to Lord Shiva.",
                "category": "culture",
                "duration_hours": 4.5,
                "estimated_cost": 800.0,
                "popularity": 90,
                "image": "https://images.unsplash.com/photo-1598324789736-4861f89564a0?auto=format&fit=crop&w=800&q=80",
                "location_name": "Elephanta Island"
            },
            {
                "name": "Marine Drive Sunset Walk & Chowpatty Chaat",
                "description": "Stroll along Queen's Necklace promenade followed by pav bhaji and kulfi on the beach.",
                "category": "food",
                "duration_hours": 2.0,
                "estimated_cost": 500.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1566552881560-0be862a7c445?auto=format&fit=crop&w=800&q=80",
                "location_name": "Marine Drive"
            }
        ]
    },
    {
        "name": "Goa",
        "country": "India",
        "region": "asia",
        "description": "Sun, sand, Portuguese churches, spice plantations, and vibrant beach shacks along the Arabian Sea.",
        "cost_index": 2,
        "popularity": 96,
        "recommended_duration_days": 4,
        "cover_image": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80",
        "latitude": 15.2993,
        "longitude": 74.1240,
        "travel_styles": "relaxed,adventure,food,solo",
        "activities": [
            {
                "name": "Calangute & Baga Beach Water Sports Combo",
                "description": "Parasailing, jet ski, banana boat ride, and bumper rides over open waves.",
                "category": "adventure",
                "duration_hours": 3.0,
                "estimated_cost": 1800.0,
                "popularity": 95,
                "image": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=800&q=80",
                "location_name": "North Goa"
            },
            {
                "name": "Old Goa UNESCO Churches & Fontainhas Latin Quarter",
                "description": "Basilica of Bom Jesus, Se Cathedral, and pastel-painted Portuguese heritage alleyways.",
                "category": "culture",
                "duration_hours": 3.5,
                "estimated_cost": 500.0,
                "popularity": 92,
                "image": "https://images.unsplash.com/photo-1587474260584-136574528ed5?auto=format&fit=crop&w=800&q=80",
                "location_name": "Panaji / Old Goa"
            },
            {
                "name": "Dudhsagar Waterfall Jeep Safari & Spice Farm Lunch",
                "description": "Off-road jungle drive to cascading 4-tiered waterfall followed by traditional Goan lunch.",
                "category": "nature",
                "duration_hours": 6.0,
                "estimated_cost": 2200.0,
                "popularity": 94,
                "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
                "location_name": "Bhagwan Mahaveer Sanctuary"
            }
        ]
    },
    {
        "name": "Paris",
        "country": "France",
        "region": "europe",
        "description": "The City of Light, world epicenter of art, haute gastronomy, timeless architecture, and romance.",
        "cost_index": 4,
        "popularity": 99,
        "recommended_duration_days": 4,
        "cover_image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "travel_styles": "culture,food,luxury,relaxed",
        "activities": [
            {
                "name": "Eiffel Tower Summit & Champagne Experience",
                "description": "Skip-the-line access to the highest observation point in Paris with glass of champagne.",
                "category": "sightseeing",
                "duration_hours": 2.5,
                "estimated_cost": 4500.0,
                "popularity": 99,
                "image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80",
                "location_name": "Champ de Mars"
            },
            {
                "name": "Louvre Museum Masterpieces Guided Tour",
                "description": "Priority entry to see the Mona Lisa, Venus de Milo, and Winged Victory with an art historian.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 5200.0,
                "popularity": 98,
                "image": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=800&q=80",
                "location_name": "Rue de Rivoli"
            },
            {
                "name": "Seine River Evening Gourmet Dinner Cruise",
                "description": "3-course French fine dining while floating past illuminated bridges and Notre-Dame cathedral.",
                "category": "food",
                "duration_hours": 2.5,
                "estimated_cost": 7800.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1509439581779-6298f75bf6e5?auto=format&fit=crop&w=800&q=80",
                "location_name": "Port de la Bourdonnais"
            }
        ]
    },
    {
        "name": "Tokyo",
        "country": "Japan",
        "region": "asia",
        "description": "Futuristic skyscrapers meet ancient shrines, neon-lit alleyways, Michelin culinary wonders, and cutting-edge tech.",
        "cost_index": 4,
        "popularity": 98,
        "recommended_duration_days": 5,
        "cover_image": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=1200&q=80",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "travel_styles": "culture,food,adventure,solo",
        "activities": [
            {
                "name": "teamLab Planets Immersive Digital Art Museum",
                "description": "Walk through water and body-immersive digital light exhibits that dissolve boundaries between art and body.",
                "category": "entertainment",
                "duration_hours": 2.5,
                "estimated_cost": 2800.0,
                "popularity": 99,
                "image": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80",
                "location_name": "Toyosu"
            },
            {
                "name": "Senso-ji Temple & Asakusa Traditional Food Tour",
                "description": "Tokyo's oldest Buddhist temple and Nakamise-dori street food tasting.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 3200.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?auto=format&fit=crop&w=800&q=80",
                "location_name": "Asakusa"
            },
            {
                "name": "Shibuya Crossing & Omoide Yokocho Izakaya Crawl",
                "description": "Experience the world's busiest pedestrian crossing followed by yakitori and sake in retro alleyways.",
                "category": "food",
                "duration_hours": 3.0,
                "estimated_cost": 3800.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=800&q=80",
                "location_name": "Shibuya & Shinjuku"
            }
        ]
    },
    {
        "name": "Dubai",
        "country": "United Arab Emirates",
        "region": "middle_east",
        "description": "Ultra-modern luxury oasis boasting soaring towers, golden sand dunes, luxury marinas, and world-class shopping.",
        "cost_index": 4,
        "popularity": 95,
        "recommended_duration_days": 3,
        "cover_image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1200&q=80",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "travel_styles": "luxury,adventure,family,shopping",
        "activities": [
            {
                "name": "Burj Khalifa 'At the Top' 148th Sky Lounge",
                "description": "Ascend the world's tallest tower with VIP lounge access and panoramic 360-degree desert and gulf views.",
                "category": "sightseeing",
                "duration_hours": 2.0,
                "estimated_cost": 8500.0,
                "popularity": 98,
                "image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=800&q=80",
                "location_name": "Downtown Dubai"
            },
            {
                "name": "Red Dune Desert Safari with BBQ Dinner & Shows",
                "description": "4x4 dune bashing, sandboarding, camel ride, belly dance performance, and Arabian feast under the stars.",
                "category": "adventure",
                "duration_hours": 6.0,
                "estimated_cost": 4200.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1451337516015-6b6e9a44a8a3?auto=format&fit=crop&w=800&q=80",
                "location_name": "Lahbab Desert"
            },
            {
                "name": "Dubai Marina Luxury Yacht Cruise",
                "description": "Glide along Dubai Marina, JBR, and Ain Dubai Ferris Wheel aboard a private yacht.",
                "category": "relaxation",
                "duration_hours": 2.5,
                "estimated_cost": 5500.0,
                "popularity": 94,
                "image": "https://images.unsplash.com/photo-1518684079-3c830dcef090?auto=format&fit=crop&w=800&q=80",
                "location_name": "Dubai Marina"
            }
        ]
    },
    {
        "name": "Singapore",
        "country": "Singapore",
        "region": "asia",
        "description": "A green garden metropolis where cutting-edge architecture harmonizes with multicultural heritage and hawker centers.",
        "cost_index": 4,
        "popularity": 94,
        "recommended_duration_days": 3,
        "cover_image": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=1200&q=80",
        "latitude": 1.3521,
        "longitude": 103.8198,
        "travel_styles": "family,food,nature,balanced",
        "activities": [
            {
                "name": "Gardens by the Bay Supertrees & Cloud Forest",
                "description": "Step into mist-veiled botanical domes and walk the OCBC Skyway amid 50-meter solar vertical gardens.",
                "category": "nature",
                "duration_hours": 3.0,
                "estimated_cost": 2900.0,
                "popularity": 98,
                "image": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=800&q=80",
                "location_name": "Marina Gardens"
            },
            {
                "name": "Chinatown & Maxwell Hawker Center Food Discovery",
                "description": "Taste Michelin-awarded Hainanese chicken rice, laksa, satay, and sugar cane juice.",
                "category": "food",
                "duration_hours": 2.5,
                "estimated_cost": 1200.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
                "location_name": "Chinatown"
            },
            {
                "name": "Night Safari Tram Ride & Wildlife Trail",
                "description": "The world's first nocturnal zoo experience to observe elephants, tigers, and tapirs in natural habitats.",
                "category": "adventure",
                "duration_hours": 3.5,
                "estimated_cost": 3800.0,
                "popularity": 95,
                "image": "https://images.unsplash.com/photo-1534567153574-2b12153a87f0?auto=format&fit=crop&w=800&q=80",
                "location_name": "Mandai"
            }
        ]
    },
    {
        "name": "London",
        "country": "United Kingdom",
        "region": "europe",
        "description": "Historic British capital brimming with royal palaces, world-class museums, West End theatre, and rich culture.",
        "cost_index": 4,
        "popularity": 96,
        "recommended_duration_days": 4,
        "cover_image": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1200&q=80",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "travel_styles": "culture,sightseeing,family,balanced",
        "activities": [
            {
                "name": "Tower of London & Crown Jewels Tour",
                "description": "Discover nearly 1,000 years of royal history, meet the Beefeaters, and view dazzling Crown Jewels.",
                "category": "culture",
                "duration_hours": 3.0,
                "estimated_cost": 4200.0,
                "popularity": 97,
                "image": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80",
                "location_name": "Tower Hill"
            },
            {
                "name": "London Eye Flight & Thames Riverbank Walk",
                "description": "Spectacular 360-degree aerial views of Big Ben, Parliament, and London skyline from 135m height.",
                "category": "sightseeing",
                "duration_hours": 2.0,
                "estimated_cost": 3900.0,
                "popularity": 95,
                "image": "https://images.unsplash.com/photo-1526129318478-62ed807ebdf9?auto=format&fit=crop&w=800&q=80",
                "location_name": "South Bank"
            },
            {
                "name": "Borough Market Artisanal Food Safari",
                "description": "Indulge in Britain's premier food market with raclette, sausage rolls, oysters, and truffle cheeses.",
                "category": "food",
                "duration_hours": 2.0,
                "estimated_cost": 2500.0,
                "popularity": 96,
                "image": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
                "location_name": "London Bridge"
            }
        ]
    }
]

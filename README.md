# MilkToastTaco
Milk Toast Taco is a Simulation Game Developed by WoofWorks Inc, Western Australia. Mainly by FunnyTom :D

Yes its ambitious, No im not downscaling! STOP TELLING ME ITS TOO BIG! ITS NOT! yes... :D


# Feature Overview!:

## Core Philosophy

MTT (MilkToastTaco) is a multi-industry sandbox game focused on deep, satisfying gameplay systems rather than flashy visuals. The game is set primarily around 2015 but features vehicles and equipment spanning from the early 1900s to the present day, with a few modern exceptions. Think of it as a "career simulator" where you can be a farmer one day, a trucker the next, and a fighter pilot on the weekend.

- **Gameplay first** - every system exists because it's fun, not because it looks cool
- **Performance over graphics** - buttery smooth framerates on mid-range hardware, no ray tracing required
- **Deep modding** - the community is the lifeblood, everything loaded from YAML/CSV/local data files. See the [XML loader documentation](core/xml_loader.py) and examples in [core/xml_loader_examples.py].
- **Career mode** - start with nothing, build a fortune across 8+ industries
- **Dynamic prices** - simple supply/demand loaded from data files, no complex NPC economy simulation
- **No NPCs** - the world reacts through physics, economy, weather, and player actions only
- **Manual labor** - if you can think of how to do it in real life, you can probably do it in MTT. Installing a part? You're turning the wrench yourself, bolt by bolt.
- **Emergent gameplay** - systems interact with each other in unexpected ways. Mud on your tires affects braking, which affects your delivery time, which affects your pay...

---

## Graphics & Physics Style

### Visual Approach

The visual style is inspired by **Farming Simulator 22** - detailed, well-modeled assets with clean textures, but lighting and post-processing are kept simple to maintain performance. The goal is a "clean" look where everything is readable and distinct, not photorealistic. Think of it like a really polished PS3/PS4-era game - everything looks good, nothing looks fake, but we're not trying to trick you into thinking it's real life.

- **Rendering configuration** - Milk Toast Taco will offer multiple rendering style options that can be configured to match user preferences and hardware capabilities.

### Mud Physics System

This is one of MTT's signature features. Inspired by Snowrunner and FS25 but pushing further:

- **Mud depth layers** - mud isn't just "on or off". There's surface puddles (shallow, barely affects handling), mid-depth mud (slows you down, tires start to sink), and deep mud (you're stuck, need a winch or another vehicle)
- **Mud types** - wet clay (sticky, hard to get out of, coats tires heavily), thick mud (slow, steady drag on movement), loose mud (tires spin easily, throw mud everywhere), dried ruts (hard surface with deep grooves, bumpy ride), standing water over mud (you don't know how deep it is until you're in it)
- **Tire interaction** - different tire treads handle mud differently. Mud tires scoop and grip, highway tires pack smooth and lose all traction, all-terrain is a compromise. Tire width matters too - wide tires float on top of soft mud better, narrow tires cut through but sink in loose mud
- **Mud accumulation** - mud physically builds up on your vehicle over time. Tires get coated first, then wheel wells, then the body. Excessive mud buildup adds weight (reducing fuel efficiency and speed), clogs radiators (engine overheating), and blocks lights
- **Cleaning** - drive through deep water to wash off most mud, use a pressure washer at a garage for complete cleaning, or just live with it. Some players might prefer the look of a well-used work truck
- **Vehicle weight effects** - a fully loaded semi truck sinks deeper than an empty pickup. A tractor with ballast weights behaves differently than one without. Weight distribution matters too - heavy front end pushes into mud differently than heavy rear
- **Winching** - when you're properly stuck, you can attach a winch cable to trees, rocks, posts, or other vehicles. Winch strength varies by vehicle. You can also use another vehicle to pull you out, but they need good traction too
- **Weather interaction** - rain makes existing mud deeper and creates new puddles. Frost freezes mud solid (great for driving, terrible for digging). Thaw turns frozen ground into a soupy mess. Extended drought dries mud out completely, turning it to dust

### Terrain Deformation

Full voxel-style terrain editing that persists across play sessions:

- **Digging** - any soil type can be excavated. Easy soil (sand, loose dirt) digs fast with basic tools. Hard soil (compacted clay, gravel) requires heavier equipment. Rock requires blasting or specialized rock-breaking tools
- **Flattening** - grade terrain for foundations, roads, or landing strips. Use a dozer blade, grader, or even a shovel for small areas
- **Mounding** - pile up excavated material. Useful for berms, dams, or just making a hill. Piles settle over time if left untouched
- **Paving** - lay down asphalt, concrete, or gravel surfaces. Requires the right materials and equipment. Roads can be painted with lane markings
- **Cut and fill** - move material from where you don't need it to where you do. Save money on material imports by using what's already on site
- **Soil types** - sand, clay, gravel, topsoil, rock, mud, frozen ground. Each has different properties for digging, compaction, and vehicle interaction
- **Erosion** - exposed soil erodes over time during rain. Slopes too steep will slowly collapse. vegetation helps stabilize soil
- **Water table** - dig deep enough and you hit water. Pump it out for construction, or use it for farming irrigation

### Weather System

Dynamic weather that affects gameplay across all industries:

- **Rain** - creates mud, reduces visibility, affects driving grip, waters crops automatically, fills water tanks, makes fishing worse (rough seas)
- **Snow** - accumulates on ground and vehicles, blocks roads, requires snow removal equipment, affects tire grip, beautiful scenery
- **Frost** - freezes mud solid (great for driving), damages unprotected crops, makes surfaces slippery, ice on water bodies
- **Wind** - affects crane operations, sailing, flying, crop damage, spreads fires
- **Fog** - reduces visibility dramatically, dangerous for driving and flying, burns off by midday usually
- **Heat waves** - crops need more water, vehicles overheat easier, fuel evaporates faster, worker fatigue increases
- **Storms** - heavy rain + wind + lightning, can start fires, damage structures, make seas dangerous
- **Seasons** - full seasonal cycle affecting vegetation, weather patterns, available activities, and prices

---

## Vehicle System

### Vehicle Damage Model

Every vehicle in MTT is made up of individual components, each with its own damage value:

- **Damage scale** - each part has a damage rating from 1 to 10. 1 is factory fresh, 10 is completely destroyed. Damage accumulates gradually from impacts, overuse, neglect, and accidents
- **Part-by-part breakdown** - a typical car has 40-80+ damageable components depending on complexity. Engine block, cylinder head, pistons, crankshaft, timing chain, water pump, alternator, starter motor, fuel injectors, exhaust manifold, catalytic converter, muffler, transmission, clutch, driveshaft, differential, axles, wheel bearings, brake pads, brake discs, brake lines, brake fluid reservoir, master cylinder, calipers, steering rack, tie rods, ball joints, shocks, struts, springs, control arms, sway bars, tires (each individually), wheels (each individually), battery, headlights, taillights, indicators, windshield (can crack/shatter), wipers, mirrors, door hinges, seat mounts, dashboard electronics, ECU, wiring harness, fuel tank, fuel lines, radiator, coolant hoses, oil pan, oil filter, air filter, cabin filter, power steering pump, AC compressor, and more
- **Total damage calculation** - all individual part damages are weighted and combined into an overall vehicle condition percentage. Engine and drivetrain parts are weighted heavier than cosmetic parts. A car with a perfect engine but dented panels might be at 85% overall. A car with a destroyed engine but perfect body might be at 20%
- **Consequential damage** - damaged parts affect other parts. A blown shock absorber causes uneven tire wear. A damaged radiator leads to engine overheating which damages the head gasket. Worn brake pads eventually damage the brake discs. Ignoring small problems leads to big problems
- **Visual damage** - body panels dent, scratch, and deform based on impact severity and location. Paint chips and fades. Windshields crack with spider-web patterns. Headlight covers crack. Bumpers sag. It's not just numbers - you can SEE the damage
- **Audio cues** - damaged engines make knocking, ticking, or grinding sounds. Worn brakes squeal. Loose exhaust rattles. Bad wheel bearings hum. The game communicates damage through sound before you even check the status screen
- **Performance impact** - damaged parts directly affect vehicle performance. Engine damage reduces horsepower and torque. Transmission damage causes rough shifting and gear slip. Tire damage reduces grip and causes vibrations. Brake damage increases stopping distance. Suspension damage affects handling and ride quality. It's not just cosmetic - a damaged vehicle FEELS different to drive

### Vehicle Buying & Selling

A deep system for acquiring and disposing of vehicles:

- **Dealerships** - physical dealership locations on the map, each with a rotating inventory. Some specialize in certain vehicle types (trucks, cars, farm equipment). Dealerships have varying prices based on their location, reputation, and current stock levels. Walk around the lot, inspect vehicles visually, check the condition report before buying
- **Online marketplace** - browse and buy vehicles from your computer or phone. Larger selection than dealerships, but you can't inspect in person until it's delivered. Shipping costs vary based on distance and vehicle size. Some online sellers are trustworthy, others might be hiding damage
- **Auction houses** - buy vehicles at auction for potentially great deals, but risk is higher. Vehicles are sold as-is, and you're bidding against other players (in multiplayer) or AI bidders. Inspect before bidding if possible, but time is limited
- **Private sales** - buy directly from other players in multiplayer. Negotiate price, inspect the vehicle in person, arrange payment and delivery. No middleman, no guarantees
- **Selling** - sell at dealerships (they take a cut, typically 15-25%), sell online (more effort but better prices), sell at auction (quick sale, unpredictable price), or sell directly to other players in multiplayer
- **Price calculation** - base vehicle value depends on make, model, year, and original condition. Modifications add or subtract value depending on quality and desirability. Mileage reduces value. Damage reduces value significantly (but not linearly - a car at 90% condition might sell for 80% of new price, while a car at 50% condition might only get 30%). Market demand affects final price
- **Vehicle history** - every vehicle tracks its ownership history, major repairs, accidents, and modifications. This history is visible to potential buyers (in multiplayer) and affects resale value. A vehicle with a clean history and documented maintenance sells for more than one with mystery repairs
- **Paperwork** - buying a vehicle requires transferring registration. You need a valid license for the vehicle class. Some vehicles require special permits (heavy trucks, commercial vehicles, aircraft). Paperwork takes time - you might buy a vehicle but can't legally use it for a day while registration processes

### Vehicle Parts System

Aftermarket parts and modifications for every vehicle:

- **Part categories** - engine internals (pistons, camshafts, turbos, superchargers), exhaust systems (headers, catalytic converters, mufflers, tip styles), suspension (springs, shocks, sway bars, lift kits, lowering kits), brakes (pads, discs, calipers, lines), tires (street, off-road, mud, sport, economy), wheels (different sizes, materials, offsets), body kits (bumpers, side skirts, hoods, spoilers, roof racks), interior (seats, steering wheels, shift knobs, gauges), lighting (headlights, light bars, underglow, tinted), performance (ECU tunes, cold air intakes, intercoolers, fuel systems), and utility (winches, toolboxes, headache racks, mud flaps)
- **Part quality tiers** - economy (cheap, basic improvement, lower durability), standard (OEM-equivalent, balanced), performance (noticeable improvement, moderate price), premium (top-tier, expensive, maximum improvement), racing (competition-only, may not be street legal)
- **Part compatibility** - not every part fits every vehicle. Parts have specific fitment based on make, model, year, and sometimes engine type. Buying the wrong part is an expensive mistake. Check compatibility before purchasing
- **Sourcing parts** - buy from auto parts stores (limited stock, immediate availability), buy online (huge selection, shipping time and cost), salvage yards (cheap used parts, variable condition, need to find and extract them yourself), machine your own (requires a machine shop, raw materials, and skill)
- **Installation methods** - see the Mechanic System section below for the full manual installation process
- **Part legality** - some modifications are illegal in certain states/regions. Exhaust noise limits, ride height restrictions, lighting colors, engine modifications, tire width limits. Get caught with illegal parts and you face fines, impound, or forced removal. Check local regulations at council buildings
- **Part deterioration** - parts wear out over time based on use. Racing hard on track wears brake pads fast. Off-roading beats up suspension. Towing heavy loads stresses the drivetrain. Regular maintenance extends part life. Some parts can be refurbished instead of replaced

### Mechanic System (Manual Part Installation)

This is where MTT gets hands-on. There is no "click to install" button. You are physically working on the vehicle:

- **Garage requirements** - you need a proper garage workspace to do serious mechanical work. A basic garage has a lift, basic tools, and a workbench. A professional garage has specialty tools, parts storage, and diagnostic equipment. You can work in a driveway for simple jobs but it's slower and more limited
- **Tool system** - every mechanical job requires specific tools, and tools have different speeds:
    - **Hand tools** (spanners, wrenches, sockets, screwdrivers) - slow but precise. Good for delicate work, tight spaces, and when you don't want to overtighten. A basic spanner might take 8-12 turns to remove a bolt. An adjustable wrench is slower than a fixed spanner because you have to adjust it first
    - **Power tools** (impact gun, electric ratchet, angle grinder) - much faster for removal and installation. An impact gun can remove a bolt in 2-3 seconds versus 30+ seconds with a hand spanner. But power tools are heavier, require batteries or air lines, and in tight spaces they might not fit. Some delicate parts shouldn't be installed with an impact gun because you might overtighten or damage them
    - **Specialty tools** (torque wrench, spring compressor, bearing press, puller sets) - required for specific jobs. You can't properly install a head gasket without a torque wrench to tighten bolts to spec. You can't change wheel bearings without a press. Forcing it without the right tool damages the part or injures you
    - **Diagnostic tools** (OBD scanner, multimeter, compression tester) - figure out what's wrong before you start replacing parts. A random misfire could be spark plugs, could be a coil pack, could be a vacuum leak. saves you from throwing parts at a problem
- **Bolt-by-bolt installation** - when you install a major component, you see every bolt:
    - Select the part from your inventory and position it on the vehicle
    - The game shows you each bolt/fastener that needs to be installed
    - You select your tool and physically turn each bolt. With a hand spanner you see the rotation animation, feel the resistance, and count the turns. With an impact gun it's quick bursts
    - Bolts have a torque spec - over-tighten and you strip the thread or snap the bolt (now you have a bigger problem). Under-tighten and it rattles loose while driving. A torque wrench gives you a satisfying click when it's right
    - Some bolts are harder to reach than others - you might need to remove other components first to access them, or use a universal joint adapter on your socket to reach around corners
    - Left-hand threads exist on some components (like left-side wheel nuts on some vehicles) - the game expects you to know or figure this out
- **Time and stamina** - mechanical work takes in-game time and costs stamina:
    - A simple oil change might take 5 minutes and barely any stamina
    - A full brake job (pads, discs, fluid) might take 20-30 minutes and use moderate stamina
    - An engine rebuild could take several hours and completely exhaust you
    - Running out of stamina means you need to rest, eat, or drink. Working while exhausted dramatically increases the chance of mistakes and injury
    - You can hire help (in multiplayer, another player) or pay a mechanic shop to do it for you (but they charge labor rates and you can't supervise quality)
- **Mistakes and injury** - things can go wrong:
    - **Stripped bolts** - overtighten or cross-thread a bolt and it's stuck. Now you need to extract it (specialty tool, extra time, frustration)
    - **Broken bolts** - snap a rusted bolt and now you're drilling it out. Much worse than a stripped bolt
    - **Pinched fingers** - working under a vehicle or around heavy components, small chance of pinching or crushing injury. Costs stamina, might require hospital visit
    - **Dropped parts** - heavy components can be dropped, damaging the part or the floor or your foot
    - **Wrong part** - install the wrong part and it doesn't fit, or worse, it fits but causes damage when you try to use it
    - **Injury severity** - minor injuries cost stamina and time. Major injuries require a hospital visit (travel time, medical costs, recovery period). Extreme injuries might prevent you from working for a while
- **Learning curve** - the game includes an in-game manual (press F10) that explains procedures for each part type. Early jobs come with step-by-step guides. As you gain experience (a hidden skill system), you get faster, make fewer mistakes, and unlock more complex procedures. A beginner changing brake pads might struggle with every bolt. An experienced player breezes through it
- **Diagnostic workflow** - before replacing parts, use diagnostic tools to identify the actual problem:
    - OBD scanner reads error codes from the ECU
    - Compression tester checks engine health
    - Multimeter checks electrical systems
    - Visual inspection reveals obvious damage
    - Listening to engine sounds can identify issues by ear
    - A proper diagnosis saves time and money compared to just replacing everything

### Fuel System

Realistic fuel management across all vehicles:

- **Fuel types** - petrol (gasoline), diesel, LPG (liquefied petroleum gas), and occasionally specialty fuels (aviation fuel for aircraft, marine diesel for boats). Each vehicle has a specific fuel type, and putting the wrong fuel in is catastrophic (and expensive to fix)
- **Fuel consumption factors** - terrain (hills use more, flat roads use less), weather (cold starts use more, hot weather can cause vapor lock), vehicle load (heavier = more fuel), driving style (aggressive acceleration burns fuel, coasting saves it), vehicle condition (damaged engine = poor fuel economy), tire pressure (under-inflated tires increase rolling resistance), aerodynamics (roof racks, towing, open windows at highway speed)
- **Fuel stations** - scattered around maps at varying distances. Prices vary by location (remote stations charge more, urban stations have more competition). Some stations are full-service, some are self-service. Fuel quality varies - cheap fuel might have contaminants that damage your engine over time
- **Fuel management** - vehicles have fuel gauges and estimated range calculations. Running on empty doesn't immediately strand you - you get sputtering, power loss, and eventually the engine dies. Carrying extra fuel in jerry cans and aftermarket long range fuel tanks is possible but has safety implications (spills, fire risk, weight)
- **Fuel storage** - build your own fuel depot on owned property. Buy fuel in bulk (cheaper per liter) and store it in tanks. Requires proper storage tanks, safety equipment, and local permits. A fuel depot is a long-term investment that saves money for heavy users
- **Fuel theft** - in multiplayer, it's possible to siphon fuel from other players' vehicles or storage tanks. Requires a siphon pump and stealth. If caught, there are consequences. Defensive measures include locking fuel caps, security cameras, and parking in secure locations
- **Fuel economy tuning** - certain vehicle modifications affect fuel economy. Bigger engines use more fuel. Turbo upgrades can improve efficiency if tuned properly. Aerodynamic mods reduce highway consumption. Eco-tires reduce rolling resistance. It's a tradeoff between performance and efficiency

---

## Career Mode - Industries

### Fishing

Start with a rod on the shore, work your way up to commanding a deep-sea trawler:

- **Shore fishing** - the simplest entry point. Buy a rod, some bait, find a good spot. Cast your line, wait for a bite, reel it in. Different fish prefer different bait, different depths, different times of day. Relaxing, low investment, but low income. Perfect for beginners or a quiet afternoon
- **Small boat fishing** - buy or rent a small fishing boat and access coastal waters. Use rod and reel for sport fish, or deploy small nets for bulk catches. Requires a basic fishing license. You need to watch weather conditions - small boats in rough seas are dangerous. Find fishing spots by exploring or getting tips from other players (multiplayer)
- **Cray pots and crab pots** - set baited pots on the sea floor, mark their GPS location, and come back later to check them. Different locations yield different catches. Pots can be stolen by other players (multiplayer) or damaged by storms. Check them regularly or you'll lose your pots and your catch. Crayfish and crabs sell for good money, especially fresh
- **Trawlers** - large commercial fishing vessels that drag nets through the water. Buy a trawler and hire crew (multiplayer, other players). Trawl different depths for different species. Manage fuel costs, crew wages, and catch quotas. Overfishing an area depletes it - you need to let stocks recover or move to new grounds. Trawlers are expensive but the income potential is massive
- **Deep sea fishing** - venture far from shore into deep waters. Big boats, big equipment, big risk. Storms are more dangerous out here. Navigation is critical - getting lost at sea is a real possibility. But the deep sea has species you can't find anywhere else, and they sell for premium prices. Requires advanced navigation equipment and seamanship skills
- **Fishing licenses** - different regions require different licenses. A basic shore license is cheap and easy. A commercial trawling license is expensive and may require completing a certain amount of fishing hours first. Some areas are protected and restrict or ban commercial fishing. Dont get caught by the Fisheries.
- **Fish processing** - catch quality matters. Fish degrade over time after being caught. Keep them in ice boxes or process them quickly. Filleting, smoking, and canning extend shelf life and increase value. A fish market pays more for processed fish than raw catch
- **Seasonal patterns** - fish populations migrate and change with seasons. Some species are only available in summer, others prefer cold winter waters. Tides affect fishing success. Full moon tides can be amazing or terrible depending on the species. Adapting your strategy to the season is key to consistent income
- **Equipment upgrades** - better rods cast further and handle bigger fish. Better boats go further and carry more. Fish finders (sonar) help locate schools of fish. Ice makers keep catch fresh longer. GPS and navigation equipment prevent getting lost. Each upgrade expands what you can do and where you can go

### Farming

From a backyard garden to industrial-scale agriculture:

- **Hobby farming** - start with a small plot of land, a basic tractor, and some seeds. Grow vegetables and herbs in your garden. Keep a few chickens for eggs. Build a greenhouse for year-round growing. It's modest income but teaches you the fundamentals. Good for learning crop rotations, soil preparation, and basic equipment operation
- **Animals** - each animal type has specific needs:
    - **Chickens** - need a coop, feed, and water. Produce eggs daily. Low maintenance, low income. Good starter animal
    - **Cattle** - need pasture, feed, water, and shelter. Produce milk (dairy) or meat (beef). Higher maintenance, higher income. Require veterinary care occasionally
    - **Pigs** - need a pen, feed, water, and mud wallows. Produce pork and manure (fertilizer). Medium maintenance, good income. They escape if pens aren't secure
    - **Sheep** - need pasture, shearing equipment, and shelter. Produce wool and meat. Medium maintenance, seasonal income (shearing schedule)
    - **Goats** - need browse (bushes, trees), shelter, and fence maintenance (they escape everything). Produce milk, cheese, and meat. Low feed cost, high labor
    - All animals need daily care: feeding, watering, health checks, shelter maintenance. Neglect leads to poor production, illness, or death. Animals have mood and health systems that affect output
- **Large acre farming** - industrial-scale production. Massive fields, massive equipment:
    - **Soil preparation** - plow, disc, harrow, and roll fields before planting. Soil testing reveals nutrient deficiencies. Apply lime, nitrogen, phosphorus, or potassium as needed. Soil quality degrades without crop rotation and proper management
    - **Planting** - use seed drills or planters to sow crops in precise rows. Different crops have different spacing and depth requirements. Planting at the wrong time of year wastes seed and labor
    - **Growing season** - crops grow over real-time days/weeks (compressed time option available). They need water (rain or irrigation), fertilizer, and weed management. Monitor growth stages and address problems quickly
    - **Harvesting** - use combines, forage harvesters, or hand-pick depending on the crop. Harvest timing matters - too early and yield is low, too late and the crop degrades. Weather during harvest is critical - rain can ruin a harvest
    - **Storage** - silos for grain, cold storage for produce, barns for hay. Proper storage maintains value. Poor storage leads to spoilage and loss
    - **Selling** - sell to local markets, processing plants, or export facilities. Prices fluctuate based on supply and demand (loaded from data files). Timing your sales can mean the difference between profit and loss
- **Niche crops** - specialized high-value production:
    - **Mushrooms** - grown indoors in controlled environments. Require specific temperature, humidity, and substrate. High value per unit but low volume. Can be grown year-round
    - **Flowers** - seasonal outdoor or year-round greenhouse production. Different varieties for different markets. Bouquet assembly adds value. Delicate - must be handled carefully
    - **Herbs** - high value, can be grown in greenhouses or small plots. Basil, rosemary, thyme, etc. Fresh herbs sell for much more than dried. Some herbs are perennial (come back every year)
    - **Specialty produce** - heirloom tomatoes, organic vegetables, microgreens, saffron. Higher labor, higher reward. Requires specific knowledge and often specific growing conditions
- **Seasonal cycles** - the full year affects farming:
    - **Spring** - soil preparation, planting, lambing season. Muddy fields make equipment operation challenging
    - **Summer** - peak growing season, irrigation management, pest control. Heat waves require extra watering
    - **Autumn** - harvest season. The busiest and most profitable time. Race against weather to get crops in
    - **Winter** - equipment maintenance, planning, animal care. Fields rest. Some winter crops (wheat, oats) continue growing slowly. Snow and frost affect animal welfare
- **Equipment fleet** - tractors (small utility to massive articulated), combines, seed drills, plows, cultivators, sprayers, irrigation systems, grain carts, wagons, telehandlers, front loaders. Each has specific capabilities and costs. Maintenance is ongoing - engines, hydraulics, implements all need care

### Trucking

From local deliveries to cross-continental haulage:

- **Local deliveries** - small trucks and vans, short routes, tight schedules. Deliver packages, furniture, groceries, and supplies around town. Navigate urban traffic, find parking, deal with tight loading docks. Low pay per delivery but high volume. Perfect for building reputation and cash flow early on
- **Long haul** - big rigs, long distances, big paydays. Haul freight across massive maps spanning multiple cities and biomes. Plan your route, manage fuel stops, deal with weather and road conditions. Fatigue system means you need to rest periodically - pull into truck stops, sleep, and continue. Oversized loads require special permits and sometimes pilot vehicles
- **Road trains** - for when one trailer isn't enough. Link multiple trailers together for maximum cargo capacity. Road trains are heavy, slow to accelerate, and hard to stop. But they carry massive amounts of freight in a single trip. Requires a powerful truck and excellent driving skills. Some roads and bridges can't handle the weight
- **Off-road delivery** - Snowrunner-style. Deliver supplies to remote locations where there are no roads. Mining camps, logging operations, research stations, disaster relief sites. Navigate mud, rivers, steep grades, and fallen trees. Recovery is your lifeline - when you get stuck, winch yourself out or call for help. High risk, high reward
- **Cargo management** - different cargo types have different requirements:
    - **Dry goods** - general freight, easy to handle, stable in transit
    - **Refrigerated** - perishable goods that need temperature-controlled trailers. Trailer must maintain temperature, uses extra fuel. If the reefer unit fails, your cargo spoils
    - **Flatbed** - oversized or irregularly shaped cargo. Must be properly secured with chains and straps. Load shifting during transit is dangerous and damages cargo
    - **Tanker** - liquid and gas cargo. Sloshing affects handling. Specialized loading and unloading procedures. Hazmat placards required for dangerous goods
    - **Livestock** - live animals need food, water, and ventilation during transport. Rough driving stresses animals. Time limits on how long animals can be in transit
    - **Oversized** - loads that exceed standard width, height, or length. Require special permits, escort vehicles, and route planning. Can't use certain roads or bridges. Slow and careful driving required
- **Truck customization** - customize your rig for the job:
    - Engine and transmission upgrades for more power or efficiency
    - Suspension modifications for load carrying or off-road capability
    - Cab comfort upgrades (better seats, entertainment systems, sleeping quarters) for long hauls
    - Utility additions (toolboxes, headache racks, light bars, air horns)
    - Exterior styling (paint, chrome, decals, exhaust stacks)
- **Trucking companies** - once you have enough capital, start your own trucking business:
    - Buy multiple trucks and hire other players (multiplayer) or manage an AI fleet
    - Contract work from various industries - farming, mining, construction, retail
    - Manage maintenance schedules, fuel costs, and vehicle replacement cycles
    - Build reputation with clients for better-paying contracts
    - Expand your fleet gradually - start with one truck, grow to a logistics empire

### Flying

From bush pilot to carrier operations:

- **Hobby flying** - start with a small Cessna or similar light aircraft. Take scenic tours, fly between small airstrips, learn the basics of flight. Low operating costs, gentle learning curve. Practice takeoffs, landings, navigation, and basic aerobatics. Perfect for learning the flight model before moving to bigger aircraft
- **Commercial aviation** - passenger airlines and cargo operations. Buy or lease airliners, manage flight schedules, hire crew (multiplayer). Keep passengers happy with smooth flights and on-time arrivals. Fuel management is critical on long routes. Deal with air traffic control, weather diversions, and mechanical issues mid-flight. Revenue comes from ticket sales and cargo space
- **Airport management** - build and operate your own airport:
    - Construct runways, taxiways, terminals, hangars, and control towers
    - Manage ground operations: fuel trucks, baggage handling, catering, de-icing
    - Set landing fees, fuel prices, and hangar rentals to attract traffic
    - Hire staff for operations, maintenance, and customer service
    - Handle emergency situations: medical diversions, mechanical failures, weather events
    - Expand your airport over time - start with a grass strip, grow to an international hub
- **Military aviation** - fighter jets, bombers, transport aircraft:
    - Fly high-performance military aircraft with realistic (but accessible) flight models
    - Air-to-air combat: intercept enemy aircraft, dogfight, patrol airspace
    - Air-to-ground: strike targets, close air support, precision bombing
    - Transport: airdrop supplies, paratroopers, vehicle extraction
    - Carrier operations: take off from and land on aircraft carriers (see Military Missions section for detailed carrier ops)
- **Bush flying** - remote area operations:
    - Fly into short, unpaved airstrips in mountains, deserts, and jungles
    - Deliver supplies to remote communities, mining camps, and research stations
    - Deal with challenging weather, terrain, and limited navigation aids
    - Some airstrips are so short and rough that only STOL (Short Takeoff and Landing) aircraft can use them
- **Flight models** - two options to suit different playstyles:
    - **Arcade mode** - simplified controls, forgiving physics, easier landings. Focus on the journey and scenery rather than technical precision. Great for beginners or casual flying
    - **Realistic mode** - full flight dynamics, stall behavior, spin recovery, crosswind landings, weight and balance. For players who want the challenge of actually flying the aircraft. Not required for progression, but rewarding to master
- **Aircraft variety** - spanning decades of aviation:
    - Light aircraft: Cessna 172, Piper Cub, de Havilland Beaver
    - Airliners: Boeing 737, Airbus A320, regional turboprops
    - Military: P-51 Mustang, F-4 Corsair, A-1 Skyraider, F-16, F/A-18, C-130 Hercules
    - Helicopters: Robinson R22, Bell 206, UH-60 Black Hawk, CH-47 Chinook
    - Specialized: crop dusters, water bombers, seaplanes, gliders

### Mining

From panning for gold to running an industrial mine:

- **Hobby mining** - start with a gold pan and a claim. Prospect for gold, gems, and minerals in streams and rivers. Use a sluice box to process more material than panning alone. Metal detecting on beaches and old mining areas. Low investment, chance of finding something valuable. Mostly luck, but knowledge of geology helps
- **Open pit mining** - industrial scale surface mining:
    - **Site preparation** - clear vegetation, strip topsoil (save it for reclamation), build access roads, establish power and water supply
    - **Drilling and blasting** - drill blast holes in patterns, load explosives, conduct controlled detonations. Safety protocols are critical - wrong blast patterns can be dangerous or inefficient. Timing delays between charges control rock fragmentation
    - **Loading and hauling** - excavators load haul trucks with blasted rock. Trucks haul ore to the processing plant and waste rock to dump sites. Cycle times, fuel consumption, and maintenance are all factors in profitability
    - **Processing** - crush and sort ore by grade. High-grade ore goes to processing, low-grade ore stockpiles for later. Different minerals require different processing methods (crushing, grinding, flotation, leaching)
    - **Reclamation** - as you mine, you restore previously mined areas. Replace topsoil, revegetate, reshape landforms. Environmental regulations require progressive reclamation. Strict enviromental regulations in cirtain juristictions, and Enviromental bonus's for cirtain actions/operations.
- **Underground mining** - when the ore body is deep:
    - **Tunnel development** - dig decline ramps, level access drives, and ventilation shafts. Ground support (rock bolts, shotcrete, mesh) prevents collapses. Poor ground conditions require heavier support
    - **Ventilation** - critical for underground safety. Fresh air must reach all working areas. Ventilation fans, ducting, and air quality monitoring. Diesel equipment underground requires more ventilation than electric
    - **Extraction methods** - cut and fill, sublevel caving, room and pillar, longwall mining. Different methods suit different ore body shapes and ground conditions
    - **Haulage** - underground trucks, rail systems, conveyor belts, and hoists move ore to surface. Equipment must fit in tight tunnels. Maintenance underground is harder than on surface
    - **Hazards** - rock falls, ground instability, water ingress, gas pockets, equipment breakdowns. Safety equipment and protocols are essential. Emergency refuge stations provide shelter if something goes wrong
- **Blasting** - controlled explosions for rock breakage:
    - **Explosive types** - ANFO (ammonium nitrate fuel oil), emulsion, dynamite, detonating cord, boosters. Each has different properties and applications
    - **Blast design** - hole diameter, depth, spacing, burden (distance to free face), stemming (material to confine explosive energy), and delay timing all affect the result
    - **Safety** - clear the blast area, sound the siren, shelter from flyrock and concussion. Misfires (unexploded charges) are dangerous and require special handling
    - **Blast results** - good blasting produces well-fragmented rock that's easy to load and process. Bad blasting produces oversized boulders (need secondary breaking) or too-fine material (waste)
- **Mineral types** - vary by region and geology:
    - Precious metals: gold, silver, platinum
    - Base metals: copper, lead, zinc, iron, aluminum
    - Industrial minerals: limestone, granite, sand, gravel, clay
    - Rare earths: lithium, cobalt, neodymium (high value, complex processing)
    - Gemstones: diamonds, rubies, emeralds, sapphires (found in specific geological settings)
- **Equipment fleet** - excavators, dozers, graders, haul trucks (rigid and articulated), drill rigs (production and exploration), loaders, crushers, screens, conveyors, pumps, generators, and ventilation equipment. Each piece requires fuel, maintenance, and skilled operation

### Boats & Maritime

From small fishing boats to massive container ships:

- **Fishing boats** - commercial fishing vessels of various sizes:
    - Small trawlers for coastal fishing, medium seiners for mid-water fish, longliners for deep-sea species. Each vessel type has different capabilities, costs, and fishing methods. Maintain your vessel, manage crew (multiplayer), and follow fishing regulations
- **Ferries** - carry passengers and vehicles across water:
    - Short-hop car ferries between nearby ports. Longer passenger ferries with amenities. Vehicle loading and unloading procedures. Schedule management and passenger satisfaction. Storm crossings test your seamanship
- **Passenger ships and cruise ships** - luxury travel on the water:
    - Manage routes, itineraries, and amenities. Keep passengers entertained and satisfied. Handle emergencies at sea (medical, mechanical, weather). Port calls and shore excursions. Revenue comes from ticket sales and onboard spending
- **Container shipping** - the backbone of global trade:
    - Load and unload containers at ports. Plan efficient routes between ports. Manage fuel consumption on long voyages. Weather routing to avoid storms. Container tracking and logistics. This is slow, methodical gameplay - the satisfaction of a perfectly planned voyage
- **Maritime law and regulations** - the rules of the sea:
    - COLREGS (collision regulations) - right of way, lights, signals
    - Port state control inspections - your vessel can be inspected at any port
    - Load line regulations - maximum loading based on season and zone
    - MARPOL - pollution prevention, garbage disposal, oil discharge
    - Manning requirements - minimum crew for vessel size and type
    - Violations result in fines, detentions, or vessel impoundment
- **Pirate encounters** - for certain regions and cargo types:
    - High-value cargo in certain waters attracts pirate attention
    - Pirate encounters range from harassment to armed boarding
    - Defenses: speed, evasive maneuvers, razor wire, locked citadels, armed security (where legal)
    - Naval escort convoys in high-risk areas
    - Ransom negotiation if captured (story mode element)
- **Sinking mechanics** - when things go badly wrong:
    - Hull breach from collision, grounding, or structural failure
    - Water ingress through damaged compartments
    - Bilge pumps fight flooding - if they can't keep up, the ship goes down
    - Damage control: seal bulkheads, patch holes, jettison cargo
    - Abandon ship: lifeboats, life rafts, immersion suits
    - Shipwrecks persist on the map and can be salvaged
    - Some wrecks become fishing spots or dive sites over time

### Vehicles & Automotive

The car culture side of MTT:

- **Tuning and modification** - see Vehicle Parts System above for detailed part installation. Performance tuning includes:
    - Engine builds (internal components, forced induction, fuel systems)
    - Suspension setup (spring rates, damping, alignment, anti-roll bars)
    - Brake upgrades (big brake kits, slotted discs, racing pads)
    - Weight reduction (stripped interiors, lightweight panels, polycarbonate windows)
    - ECU tuning (fuel maps, boost pressure, rev limits, launch control)
    - Each modification affects vehicle behavior - a car tuned for track use is terrible on the street and vice versa
- **Racing** - organized competitive events:
    - **Circuit racing** - track days and championships at dedicated circuits. Time trials, endurance races, sprint races. Vehicle preparation is critical - race vehicles need specialized parts and setup
    - **Rally** - point-to-point stages on varied surfaces (tarmac, gravel, dirt, snow). Navigation and pace notes are essential. Damage carries over between stages - finish fast but finish in one piece
    - **Drag racing** - pure acceleration. Bracket racing or heads-up. Tire choice, launch technique, and engine tuning determine success. The burnout box is your friend
    - **Drift events** - style and angle over pure speed. Judged on line, angle, speed, and style. Rear-wheel drive, high power, and a willingness to destroy tires
    - **Hill climbs** - timed ascent of a hill or mountain road. One shot, no practice runs on race day. Mixed surfaces and tight corners test driver skill
- **Off-road competitions** - testing vehicle capability and driver skill:
    - **Mud bogging** - drive through progressively deeper and thicker mud pits. Modified trucks with massive tires and high horsepower. Getting stuck is part of the fun - sometimes you need a tow
    - **Rock crawling** - navigate extreme terrain at slow speed. Articulation, traction, and throttle control are everything. Vehicles are heavily modified with lockers, low-range gearing, and winch points
    - **Hill climbs** - steep, loose, and slippery. Power and traction battle gravity. The hill always wins eventually
    - **Overland challenges** - multi-day navigation events through remote terrain. Self-recovery skills, camp setup, and navigation are as important as driving
- **Exploration** - discover the world:
    - Hidden locations: abandoned mines, secret beaches, mountain summits, old barns with classic cars
    - Wreck recovery: find crashed or abandoned vehicles and restore them
    - Photography challenges: capture specific locations or events
    - The maps are large and rewarding to explore - there's always something around the next corner
- **Rescue and recovery** - help others (or yourself):
    - Vehicle recovery: winch stuck vehicles out of mud, ditches, and rivers. Assess the situation, choose attachment points, and pull carefully
    - Roadside assistance: flat tires, dead batteries, locked keys in the car. Simple jobs but steady income
    - Heavy recovery: upright rolled trucks, extract vehicles from buildings, recover vehicles from water. Requires specialized equipment and skill
    - Emergency response: assist at accident scenes, clear debris from roads. Sometimes you're the only one who can help
- **Towing** - a business in itself:
    - Light duty: cars that broke down, parked illegally, involved in minor accidents
    - Medium duty: vans, small trucks, SUVs
    - Heavy duty: semi trucks, buses, construction equipment. Requires a big wrecker and serious skill
    - Impound: relocate illegally parked or abandoned vehicles. Some owners are not happy about this
    - Storage yard management: impounded vehicles need to be stored, maintained (battery on trickle charge, tires inflated), and eventually disposed of if unclaimed
- **Street racing** - the underground scene:
    - Find race events through word of mouth (multiplayer) or scattered flyers
    - Organized events at abandoned industrial areas, mountain roads, or empty parking lots
    - Buy-in fees and prize pools. Risk your entry fee for a chance at big payouts
    - Police attention increases with repeated street racing activity. Get caught and face impound, fines, or vehicle seizure
    - Vehicle preparation: stripped-down street cars, specific tire choices, tuning for the specific course
    - The community is tight-knit. Build reputation to get invited to better events with bigger payouts
- **Machining custom parts** - build what you can't buy:
    - Machine custom components from raw materials (bar stock, castings, forgings)
    - Equipment: lathe, milling machine, drill press, grinder, welder, plasma cutter
    - Design parts using in-game CAD tools (simplified 3D modeling)
    - Custom parts can be unique one-offs or production runs for sale
    - Requires skill development and material sourcing
    - Some parts can only be made custom - there's no off-the-shelf solution

### Construction

Build the world, one nail at a time:

- **Residential construction** - build houses from foundation to finish:
    - **Site preparation** - clear the lot, grade the terrain, lay out the foundation
    - **Foundation** - dig footings, pour concrete, install reinforcement. Slab, pier, or basement foundation options
    - **Framing** - cut lumber, nail together walls, install floor and roof joists. Structural integrity matters - wrong measurements or weak connections cause problems later
    - **Roofing** - install trusses, sheathing, underlayment, and shingles/tiles/tin roofing. Working at height requires safety equipment. Different roofing materials have different installation methods and costs
    - **Siding and exterior** - install cladding, trim, windows, and doors. Weather sealing is critical. Different materials (vinyl, wood, brick, stone) have different installation techniques
    - **Plumbing** - run water lines, install fixtures (sinks, toilets, showers, tubs), connect to sewer/septic. Pressure testing required. Hot water systems, water heaters, and filtration
    - **Electrical** - run wiring, install outlets, switches, light fixtures, and breaker panels. Code compliance is mandatory. Different circuits for different loads. Smoke detectors.
    - **HVAC** - heating, ventilation, and air conditioning. Ductwork, unit placement, thermostat installation. Climate control is essential for occupant comfort
    - **Interior finishing** - drywall, paint, trim, flooring, cabinetry, countertops. The final touches that make a house a home. Quality of finish affects property value
- **Commercial and industrial construction** - bigger projects, bigger equipment:
    - **Steel frame buildings** - warehouses, factories, large retail spaces. Steel erection requires cranes and specialized crews
    - **Concrete construction** - tilt-up panels, reinforced concrete, post-tensioned slabs. Commercial-grade foundation and structural work
    - **Road construction** - excavation, base preparation, asphalt or concrete paving, line marking, signage, curbs and gutters. Multi-lane highways, roundabouts, intersections
    - **Bridge construction** - beams, arches, suspension designs. Engineering challenges and aesthetic considerations
- **DIY and renovation** - smaller scale, personal projects:
    - Bathroom remodels, kitchen upgrades, room additions
    - Deck building, fence installation, landscaping
    - Home automation and smart systems
    - Solar panel installation and battery storage
    - Insulation upgrades, window replacement
    - Every project has a budget and timeline. Quality materials cost more but last longer. Shoddy work looks bad and fails early
- **Material sourcing** - where do you get your supplies?
    - **Hardware stores** - walk in, browse shelves, buy what you need. Convenient but limited stock and higher prices
    - **Building supply yards** - bulk materials at better prices. Lumber, concrete, roofing, plumbing supplies. Need a truck or trailer to haul
    - **Specialty suppliers** - electrical wholesale, plumbing wholesale, HVAC suppliers. Trade pricing for bulk orders
    - **Online ordering** - wide selection, delivered to site. Lead times and delivery costs apply
    - **Salvage and reuse** - demolished buildings yield usable materials. Reclaimed wood, vintage fixtures, recycled concrete. Sustainable and cheaper
- **Equipment** - the tools of the trade:
    - **Hand tools** - hammers, saws, drills, levels, measuring tapes. Essential for finish work
    - **Power tools** - circular saws, reciprocating saws, impact drivers, nail guns. Faster and more powerful
    - **Heavy equipment** - excavators, dozers, loaders, cranes, concrete pumps, telehandlers. For moving earth and materials at scale
    - **Specialty equipment** - concrete saws, core drills, laser levels, surveying equipment. For specific tasks that require precision
    - Equipment can be rented for short-term use or purchased for ongoing projects. Rental is cheaper for one-off jobs, purchase is better for frequent use
- **Council and public works** - government contracts:
    - Road maintenance and construction
    - Public building construction and renovation
    - Park and recreation facility development
    - Utility infrastructure (water, sewer, power)
    - Disaster recovery and rebuilding
    - Contracts are awarded based on bid price, reputation, and capability. Lower bids win but leave less profit margin. Quality work builds reputation for future contracts

---

## Military Missions

### Overview

Military missions are a separate gameplay mode from the main career world. They take place in historically-inspired settings spanning from World War I to modern conflicts, though the main game is set around 2015. Think of these as "war stories" - self-contained missions and campaigns that let you experience different eras of military aviation and ground combat.

- **Separate from career** - military missions have their own progression, unlocks, and rewards. Your career mode money, vehicles, and equipment don't carry over (and vice versa). It's a completely separate game mode
- **Historical settings** - missions set in WWI (1914-1918), WWII (1939-1945), Korean War (1950-1953), Vietnam War (1955-1975), Cold War (1947-1991), Gulf War (1990-1991), and modern conflicts
- **Era-appropriate equipment** - you fly period-accurate aircraft with era-appropriate weapons and technology. No GPS in a Spitfire, no radar on a Camel. You navigate by map and compass, identify targets by eye, and dogfight with machine guns
- **Badge system** - earn badges for completing missions, achieving objectives, and demonstrating skill. See Badge section below
- **Random encounters** - missions aren't entirely scripted. Enemy patrols, weather events, mechanical failures, and friendly force movements have random elements. No two playthroughs are exactly the same
- **Difficulty scaling** - missions range from introductory (learn the basics) to expert (realistic damage models, limited ammunition, complex navigation). Difficulty affects enemy actions, accuracy, damage models, and available support
- **Briefing and debriefing** - each mission starts with a detailed briefing (maps, objectives, known threats, friendly positions) and ends with a debrief (performance review, medal considerations, lessons learned)

### World War I (1914-1918)

The dawn of aerial combat:

- **Aircraft** - Sopwith Camel, Fokker Dr.I, SPAD XIII, Albatros D.III, Royal Aircraft Factory S.E.5, Fokker D.VII. Biplanes and triplanes with rotary or inline engines. Maximum speeds of 100-130 mph. Armament: synchronized machine guns (Vickers, Spandau, Lewis)
- **Mission types**:
    - **Reconnaissance** - fly over enemy lines, photograph positions, report back. Minimal armament, maximum skill in avoidance. The observer in two-seat aircraft uses a camera and pistols
    - **Fighter patrol** - sweep the skies for enemy aircraft. Dogfighting in WWI is intimate and personal - you can see the other pilot's face. Stall speeds are high relative to maximum speed, making every maneuver risky
    - **Ground attack** - strafe trenches and supply lines with machine guns. Low altitude, heavy anti-aircraft fire from ground troops. Flying Circus missions with colorful aircraft
    - **Bomber escort** - protect slow, vulnerable bombers on strategic raids. Enemy fighters will try to intercept. Keep them alive at all costs
    - **Trench strafing** - extremely low-level flight along enemy trenches. Exhilarating and dangerous. Ground fire is intense
- **Carrier operations** - WWI naval aviation was primitive:
    - Take off from makeshift wooden platforms on converted ships
    - Landing on pitching, rolling decks with no arresting gear
    - Limited fuel means short sorties
    - Aircraft are fragile - a few bullet hits can bring you down
- **Challenges** - no radios (communication by visual signals), no radar, weather dependent, unreliable engines, limited ammunition. Survival is achievement enough

### World War II (1939-1945)

The golden age of piston-engine combat:

- **Aircraft** - P-51 Mustang, Spitfire, Messerschmitt Bf 109, F4U Corsair, A-1 Skyraider, B-17 Flying Fortress, Lancaster bomber, Zero. More powerful engines, heavier armament, more sophisticated systems
- **Mission types**:
    - **Air superiority** - establish control of the airspace. Sweep for enemy fighters, engage in large-scale dogfights
    - **Close air support** - support ground troops by attacking enemy positions. Coordinate with ground forces (radio communication available in WWII)
    - **Strategic bombing** - high-altitude precision (or area) bombing of industrial targets. Manage formation flying, deal with flak and enemy interceptors
    - **Carrier operations** - launch from and recover to aircraft carriers. Arrested landings, catapult launches, deck spotting
    - **Night fighting** - equipped with early radar, hunt enemy bombers in the dark.
    - **Submarine patrol** - hunt enemy shipping from the air. Spot periscopes, drop depth charges, strafe deck guns
    - **Photo reconnaissance** - unarmed, high-altitude photography missions. Speed and altitude are your only defense
- **Carrier operations** - WWII carriers were busy places:
    - Catapult launches with JATO (Jet Assisted Take-Off) rockets for heavily loaded aircraft
    - Arrested landings with wire systems. Hook the wire or bolter (go around)
    - Deck crews color-coded by function (ordnance, fuel, maintenance, flight deck)
    - Operations pause during combat damage - if the carrier is hit, flight deck operations stop
    - Multiple carriers in a task force - coordinate strikes across a group
- **Progression** - start in early-war aircraft (biplanes, early monoplanes), progress to late-war fighters and bombers. Earn promotions and medals through successful missions

### Korean War (1950-1953)

The jet age begins:

- **Aircraft** - F-86 Sabre, MiG-15, F9F Panther, B-29 Superfortress, P-51 Mustang (still in service). First generation jets alongside late piston-engine aircraft
- **Mission types**:
    - **MiG Alley** - high-altitude jet combat over "MiG Alley" in northwestern Korea. F-86 vs MiG-15 dogfights at 40,000 feet
    - **Ground attack** - close air support for ground forces. F-9F Panthers and piston-engine aircraft attack ground targets
    - **B-29 strategic bombing** - night raids on industrial targets. Defensive gunners deal with enemy night fighters
    - **Reconnaissance** - high-altitude photo reconnaissance over enemy territory
- **New challenges** - jet engines are more powerful but less responsive at low speed. Early ejection seats. Radar-directed anti-aircraft fire

### Vietnam War (1955-1975)

The helicopter war and high-tech air combat:

- **Aircraft** - F-4 Phantom, A-1 Skyraider, A-4 Skyhawk, F-105 Thunderchief, UH-1 Huey, AH-1 Cobra, CH-47 Chinook, B-52 Stratofortress
- **Mission types**:
    - **Rolling Thunder** - sustained bombing campaign against North Vietnamese targets. Heavy anti-aircraft defenses, SAM (Surface-to-Air Missile) threats
    - **Linebacker** - intensified bombing with B-52 Arc Light strikes. Massive formations, heavy defenses
    - **Close air support** - support ground troops in jungle terrain. Forward air controllers (FACs) mark targets with smoke
    - **Helicopter operations** - assault troop insertion, medevac, resupply, gunship support.
    - **Search and rescue** - locate and extract downed pilots behind enemy lines. Dangerous, high-stakes missions
    - **Arc Light** - B-52 strategic bombing from high altitude. Carpet bombing with massive ordnance loads
    - **Fast FAC** - fast jet forward air control, marking targets for strike aircraft in contested airspace
- **New threats** - SAM missiles (SA-2 Guideline), AAA (anti-aircraft artillery) in massive quantities, MiG-21 interceptors, MiG-17 fighter-bombers. Electronic countermeasures (ECM) become essential
- **Special operations** - MACV-SOG reconnaissance teams, covert operations, air commando missions

### Cold War (1947-1991)

Tension and technology:

- **Aircraft** - F-14 Tomcat, F-15 Eagle, F-16 Fighting Falcon, F/A-18 Hornet, SR-71 Blackbird, B-52, A-10 Thunderbolt II, F-117 Nighthawk
    
- **Mission types**:
    
    - **Air policing** - intercept and escort Soviet bombers and reconnaissance aircraft during the Cold War
    - **NATO defense** - defend Western Europe against potential Soviet invasion. Large-scale air battles
    - **Carrier battle group operations** - full carrier air wing operations in potential conflict zones
    - **Reconnaissance** - U-2 and SR-71 high-altitude reconnaissance over hostile territory
    - **Specialized strike** - precision strike with new guided munitions. Laser-guided bombs, early cruise missiles
    - **SEAD (Suppression of Enemy Air Defenses)** - hunt and destroy SAM sites. Dangerous but critical missions
- **Technology evolution** - radar-guided missiles, beyond visual range combat, electronic warfare, stealth technology emerging
    
- **Play Both Sides** - Complete operations by the United States and the USSR and there allies.
    
    ### Gulf War & Modern (1990-present)
    
    High-tech warfare:
    
- **Aircraft** - F-14, F-15, F-16, F/A-18, A-10, F-117, B-2 Spirit, AH-64 Apache, modern variants
    
- **Mission types**:
    
    - **Desert Storm** - massive air campaign to liberate Kuwait. Precision strikes, SCUD hunting, air superiority
    - **Close air support** - A-10 Warthog tank-busting, Apache helicopter strikes
    - **Deep strike** - F-117 stealth night attacks on high-value targets
    - **SCUD hunt** - mobile missile launcher hunting in the Iraqi desert
    - **Peacekeeping operations** - no-fly zone enforcement, combat air patrol
    - **Modern conflicts** - counter-insurgency, close air support in urban environments, drone operations
- **Modern technology** - GPS-guided munitions, targeting pods, data linking, network-centric warfare, stealth
    

### Badge System

Earn badges for exceptional performance across all military missions:

- **Wings badges** - awarded for completing pilot training in each era:
    
    - WWI Pilot Wings
    - WWII Pilot Wings
    - Korean War Jet Wings
    - Vietnam War Wings
    - Cold War Wings
    - Modern Combat Wings
- **Mission completion badges** - for completing specific mission types:
    
    - Reconnaissance Badge (complete 10 recon missions)
    - Ground Attack Badge (destroy 50 ground targets)
    - Air-to-Air Badge (achieve 25 aerial victories)
    - Bomber Badge (complete 20 bombing missions)
    - Helicopter Badge (complete 15 helicopter missions)
    - Carrier Operations Badge (complete 10 carrier launches and recoveries)
- **Skill badges** - for exceptional performance:
    
    - Ace Badge (5 aerial victories in a single mission)
    - Sharpshooter Badge (80%+ accuracy in ground attack)
    - Navigator Badge (complete 10 missions using only map and compass)
    - Night Owl Badge (complete 10 night missions)
    - Weather Warrior Badge (complete 5 missions in severe weather)
- **Campaign badges** - for completing full campaign arcs:
    
    - WWI Campaign Badge (complete all WWI missions)
    - WWII European Theater Badge
    - WWII Pacific Theater Badge
    - Korean War Campaign Badge
    - Vietnam War Campaign Badge
    - Cold War Campaign Badge
    - Desert Storm Campaign Badge
- **Special badges** - rare achievements:
    
    - Zero Loss Badge (complete a campaign without losing an aircraft)
    - Wings of Legend Badge (earn all other badges)
    - Historical Ace Badge (replicate a famous ace's score in their aircraft)
    - Eagle Eye Badge (spot and engage a target beyond visual range)
- **Badge display** - earned badges display on your pilot profile in multiplayer. Show off your accomplishments. Some badges unlock special aircraft liveries or cosmetic items Badges are displayed in your Career Mode Gameplay.
    

### Random Encounter System

Missions aren't fully scripted - the world reacts dynamically:

- **Enemy patrol patterns** - enemy aircraft and ground units follow general patterns but with random variation. You might encounter a patrol where none was expected, or find a route undefended
- **Weather events** - dynamic weather can ground flights, create navigation challenges, or provide cover for attacks
- **Mechanical failures** - aircraft can develop problems mid-mission. Engine trouble, hydraulic leaks, battle damage leading to system failures. Adapting to failures separates good pilots from great ones
- **Friendly force movements** - allied units move and fight independently. Sometimes they need your help, sometimes they provide unexpected support
- **Random objectives** - secondary objectives appear during missions. Rescue a downed pilot, destroy a target of opportunity.
- **Intel variation** - mission briefings provide general information, but the exact enemy disposition varies. Recon data might be outdated or incomplete

---

## Modding System (FS22-style)

MTT is designed from the ground up to be moddable:

- **Custom vehicles** - import your own 3D models with custom stats. Define engine specs, weight, dimensions, damage thresholds, part compatibility, and more in YAML files.
    
- **Custom maps** - create entire worlds. Define terrain, roads, buildings, industries, and spawn points. Maps can be any size and theme (rural, urban, desert, arctic, tropical)
    
- **Custom equipment** - tools, machines, implements, and attachments. Define working width, speed, power requirements, and fuel consumption
    
- **Custom parts** - engine components, suspension parts, body kits, and more. Define compatibility, performance effects, and visual changes
    
- **Data-driven** - all game data lives in YAML and CSV files:
    
    - prices.yaml - vehicle, part, and commodity prices
    - vehicle_stats.yaml - performance specifications
    - regulations.yaml - legal requirements per region
    - mud_physics.yaml - mud types and behaviors
    - soil_types.yaml - terrain properties
    - fish_species.yaml - fish data
    - crop_types.yaml - crop growth data
    - equipment_stats.yaml - tool specifications
    - military_missions.yaml - mission definitions
    - badges.yaml - badge requirements
    - Modders can add new entries or modify existing ones without touching code
- **No compile required** - drop mods in a folder, enable in the launcher. The game scans mod folders on startup and loads all valid mods. Invalid mods are logged with helpful error messages
    
- **Mod structure**:
    
    ```
    mods/
      MyAwesomeMod/
        mod.yaml          - mod metadata (name, version, description, author)
        vehicles/
          my_truck.yaml   - vehicle definition
          my_truck/       - 3D model and textures
        parts/
          turbo_kit.yaml  - custom part
        maps/
          my_map.yaml     - map definition
        textures/
          my_texture.png  - shared textures
    ```
    
- **Script mods** - add new gameplay systems:
    
    - Lua plugin system for deep game integration
    - Custom UI elements, menus, and HUD components
    - New industry types, mission types, and career paths
    - AI behaviors and vehicle physics modifications
    - Community API documentation included
- **Mod marketplace** (post-release) - community platform for sharing and discovering mods:
    
    - Rating and review system
    - Dependency management (mod A requires mod B)
    - Version tracking and automatic updates
    - Featured mods and creator spotlights
- **Compatibility** - mods are versioned. When the game updates, older mods may need updates. The mod loader detects incompatible mods and warns the player
    

---

## Future Features (post-release)

Features planned for post-launch updates:

- **Story Mode** - narrative-driven campaign with characters, plot, and branching storylines. Start as a newcomer in a small town, work your way up through the industries, deal with rivals, build relationships, and uncover mysteries. Multiple storylines that intersect and branch based on player choices
- **Multiplayer** - full multiplayer support:
    - **Local Multiplayer** - Up to 4 players on splitscreen and up to 15 in LAN mode.
    - Work Together in a comany, or go off on your own and fight to be the best.
- **Dynamic events** - world events that affect gameplay:
    - Natural disasters (floods, bushfires, earthquakes, storms)
    - Economic shifts (market crashes, booms, shortages)
    - Construction projects (new roads, buildings, infrastructure appearing over time)
    - Seasonal events (harvest festivals, fishing tournaments, racing championships)
- **Radio and music system** - in-game audio:
    - Multiple radio stations with different genres
    - Custom music folder support (drop your own MP3s in)
    - Dynamic radio that reacts to gameplay (traffic reports, weather updates, news)
    - Two-way radio for trucking and aviation communications
- **Photo mode** - capture beautiful moments:
    - Free camera, depth of field, filters
    - Share screenshots directly to social media
    - Photography contests in multiplayer



© 2026 FunnyTom777. All rights reserved.

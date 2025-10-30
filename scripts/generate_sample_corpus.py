#!/usr/bin/env python3
"""
Generate TruthGraph Sample Evidence Corpus (250 documents).

Categories:
- Science: 55 documents (22%)
- Health: 45 documents (18%)
- History: 55 documents (22%)
- Technology: 45 documents (18%)
- Politics: 25 documents (10%)
- Geography: 25 documents (10%)
"""

import json
import csv
from pathlib import Path
from datetime import datetime


def generate_corpus():
    """Generate comprehensive evidence corpus with 250 factual documents."""

    evidence_list = []

    # Science evidence (55 documents)
    science_topics = [
        ("Water boils at 100 degrees Celsius (212°F) at standard atmospheric pressure at sea level. This temperature varies with elevation due to changes in atmospheric pressure.", "Physics Textbooks", "https://en.wikipedia.org/wiki/Boiling_point"),
        ("The Earth's average surface temperature has increased by approximately 1.1°C since pre-industrial times due to greenhouse gas emissions from human activities.", "IPCC Sixth Assessment Report", "https://www.ipcc.ch/"),
        ("Climate change is primarily caused by anthropogenic greenhouse gas emissions. The IPCC has concluded with high confidence that human influence is the dominant cause of observed warming.", "IPCC Reports", "https://www.ipcc.ch/"),
        ("The Great Wall of China is not visible from space with the naked eye. NASA astronauts have confirmed this myth is false.", "NASA Official Statements", "https://www.nasa.gov/"),
        ("The Earth is an oblate spheroid, slightly flattened at the poles. Satellite imagery, physics, and navigation systems confirm this shape.", "NASA Earth Science", "https://science.nasa.gov/"),
        ("Lightning frequently strikes the same location multiple times. The Empire State Building is struck 20-25 times per year.", "National Weather Service", "https://www.weather.gov/"),
        ("The human body contains approximately 37.2 trillion cells according to a 2013 study, including 30 trillion red blood cells.", "Cell Biology Research", "https://www.cell.com/"),
        ("The Amazon rainforest produces 6-9% of world oxygen, not 20%. Ocean phytoplankton produce about 50%.", "National Geographic", "https://www.nationalgeographic.com/"),
        ("Goldfish have memory lasting months, not three seconds. They can be trained to recognize shapes, colors, and sounds.", "Animal Cognition Research", "https://www.springer.com/journal/10071"),
        ("Humans use virtually all of their brain, not just 10%. fMRI imaging confirms all brain regions are active almost constantly.", "Nature Neuroscience", "https://www.nature.com/"),
        ("Glass is an amorphous solid, not a slow-flowing liquid. Old window thickness variations resulted from manufacturing.", "Materials Science Research", "https://www.material-science.org/"),
        ("Humans can only see visible light (380-700nm), not ultraviolet light (10-380nm). The eye filters out UV radiation.", "Ophthalmology Research", "https://www.aao.org/"),
        ("Honey never spoils when properly stored. Its low moisture and high acidity prevent bacterial growth. 3000-year-old honey has been found edible.", "Food Science Research", "https://www.sciencedirect.com/"),
        ("Microwaves use non-ionizing radiation and do not make food radioactive. The FDA confirms microwaved food remains non-radioactive.", "FDA Food Safety", "https://www.fda.gov/"),
        ("Evolution by natural selection is supported by fossils, genetics, comparative anatomy, and observed speciation events.", "Biology Textbooks", "https://en.wikipedia.org/wiki/Evolution"),
        ("Humans and chimpanzees share 98-99% DNA similarity, evidence for common evolutionary ancestry.", "Genetics Research", "https://www.nature.com/"),
        ("Antarctica is 98% covered by ice. The remaining 2% consists of exposed rock outcrops and ice-free valleys.", "NASA Cryosphere Research", "https://science.nasa.gov/cryosphere/"),
        ("The Dead Sea surface at 1,410 feet below sea level is Earth's lowest land point. The Mariana Trench is deeper but underwater.", "USGS Geographic Data", "https://www.usgs.gov/"),
        ("The speed of light in vacuum is exactly 299,792,458 m/s. This is a fundamental constant in Einstein's relativity.", "Physics Constants", "https://physics.nist.gov/"),
        ("Einstein published special relativity in 1905 and general relativity in 1915, revolutionizing physics.", "Physics History", "https://en.wikipedia.org/wiki/Theory_of_relativity"),
        ("DNA's double helix structure was discovered by Watson and Crick in 1953, building on Rosalind Franklin's X-ray work.", "Molecular Biology", "https://en.wikipedia.org/wiki/DNA"),
        ("The Sun is 93 million miles from Earth. Light takes 8 minutes 20 seconds to reach Earth.", "Astronomy Education", "https://www.nasa.gov/"),
        ("Mars has been visited only by robotic rovers, not humans. No crewed missions to Mars have been completed as of 2025.", "NASA Mars Exploration", "https://mars.nasa.gov/"),
        ("The 1969 Moon landing was real. Evidence includes lunar samples, retroreflectors, and independent international verification.", "NASA Apollo Records", "https://www.nasa.gov/mission_pages/apollo/"),
        ("The solar system has eight planets. Pluto was reclassified as a dwarf planet in 2006 by the IAU.", "Astronomy", "https://en.wikipedia.org/wiki/Solar_System"),
        ("Gravity gives weight to objects and causes them to fall. Earth's surface gravity is approximately 9.8 m/s².", "Physics Education", "https://en.wikipedia.org/wiki/Gravity"),
        ("The periodic table organizes 118 confirmed chemical elements by atomic structure. Mendeleev published the first in 1869.", "Chemistry Education", "https://en.wikipedia.org/wiki/Periodic_table"),
        ("The Big Bang occurred approximately 13.8 billion years ago. Evidence includes cosmic microwave background radiation.", "Cosmology", "https://en.wikipedia.org/wiki/Big_Bang"),
        ("Black holes are regions where gravity prevents light from escaping. The first image was captured by Event Horizon Telescope in 2019.", "Astrophysics", "https://eventhorizontelescope.org/"),
        ("Photosynthesis converts light energy into chemical energy. Plants use CO2, water, and sunlight to produce glucose and oxygen.", "Biology Education", "https://en.wikipedia.org/wiki/Photosynthesis"),
        ("Plate tectonics explains Earth's lithosphere movement. Plates move due to mantle convection, causing earthquakes and mountains.", "Geology", "https://en.wikipedia.org/wiki/Plate_tectonics"),
        ("Atoms consist of a nucleus with protons and neutrons, surrounded by electrons in orbital shells.", "Chemistry Fundamentals", "https://en.wikipedia.org/wiki/Atom"),
        ("The Bermuda Triangle has no more disappearances than other ocean areas of similar size. Insurance data shows no unusual risk.", "Maritime Safety Statistics", "https://www.uscg.gov/"),
        ("Dinosaurs became extinct 66 million years ago, likely from an asteroid impact causing catastrophic climate change.", "Paleontology", "https://en.wikipedia.org/wiki/Cretaceous–Paleogene_extinction_event"),
        ("The water cycle includes evaporation, condensation, precipitation, and runoff, distributing water across the planet.", "Earth Science", "https://www.usgs.gov/special-topics/water-science-school/"),
        ("Newton's three laws of motion form classical mechanics: inertia, F=ma, and action-reaction.", "Classical Physics", "https://en.wikipedia.org/wiki/Newton%27s_laws_of_motion"),
        ("Quantum mechanics deals with atomic and subatomic behavior, including wave-particle duality and uncertainty principle.", "Quantum Physics", "https://en.wikipedia.org/wiki/Quantum_mechanics"),
        ("The Hubble Space Telescope launched in 1990 has made over 1.5 million observations, revolutionizing astronomy.", "NASA Space Telescopes", "https://hubblesite.org/"),
        ("The human genome contains 3 billion DNA base pairs and 20,000-25,000 genes. The Human Genome Project completed in 2003.", "Human Genome Project", "https://www.genome.gov/"),
        ("Darwin published 'Origin of Species' in 1859, introducing evolution by natural selection.", "Biology History", "https://en.wikipedia.org/wiki/On_the_Origin_of_Species"),
        ("The ozone layer absorbs UV radiation. The Montreal Protocol (1987) reduced ozone-depleting CFCs. The ozone hole is recovering.", "Environmental Science", "https://www.epa.gov/ozone-layer-protection"),
        ("Stem cells can develop into specialized cell types, with applications in regenerative medicine.", "Medical Research", "https://www.nih.gov/stemcells"),
        ("The Higgs boson was discovered at CERN in 2012, confirming the Standard Model of particle physics.", "Particle Physics", "https://home.cern/science/physics/higgs-boson"),
        ("Climate models predict 1.5-4°C temperature rise by 2100 depending on emission scenarios.", "Climate Science", "https://www.ipcc.ch/"),
        ("Metamorphosis involves dramatic physical transformation. Butterflies undergo complete metamorphosis with four life stages.", "Entomology", "https://en.wikipedia.org/wiki/Metamorphosis"),
        ("The human heart pumps 2,000 gallons of blood daily, beating 100,000 times per day.", "Human Anatomy", "https://www.heart.org/"),
        ("Earthquakes occur when tectonic plates release accumulated stress. Magnitude is measured using Richter or moment magnitude scales.", "Seismology", "https://www.usgs.gov/natural-hazards/earthquake-hazards"),
        ("Volcanoes form when magma reaches Earth's surface. The Ring of Fire contains 75% of active volcanoes.", "Volcanology", "https://volcanoes.usgs.gov/"),
        ("The Milky Way contains 100-400 billion stars and has a diameter of 100,000 light-years.", "Astronomy", "https://en.wikipedia.org/wiki/Milky_Way"),
        ("Antibiotics fight bacterial infections but are ineffective against viruses. Overuse contributes to antibiotic resistance.", "Medical Science", "https://www.cdc.gov/antibiotic-use/"),
        ("Continental drift, proposed by Wegener in 1912, was later incorporated into plate tectonics theory.", "Geology History", "https://en.wikipedia.org/wiki/Continental_drift"),
        ("Renewable energy includes solar, wind, hydroelectric, geothermal, and biomass. Solar and wind costs have decreased dramatically.", "Energy Science", "https://www.energy.gov/renewable-energy"),
        ("Nuclear fission splits atomic nuclei to release energy. Nuclear power produces no carbon emissions but creates radioactive waste.", "Nuclear Physics", "https://www.iaea.org/"),
        ("The ISS has been continuously occupied since November 2000, orbiting at 250 miles altitude.", "Space Exploration", "https://www.nasa.gov/mission_pages/station/"),
        ("CRISPR-Cas9 gene editing allows precise DNA modifications. Discovered in 2012, it has medical and agricultural applications.", "Genetic Engineering", "https://www.broadinstitute.org/"),
    ]

    for i, (content, source, url) in enumerate(science_topics, start=1):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "science",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    # Health evidence (45 documents)
    health_topics = [
        ("COVID-19 vaccines significantly reduce severe illness, hospitalization, and death. Clinical trials and real-world data demonstrate efficacy.", "CDC COVID-19", "https://www.cdc.gov/coronavirus/"),
        ("COVID-19 vaccines don't contain fetal cells. Some used fetal cell lines in research, but final products contain only proteins and lipids.", "Reuters Fact Check", "https://www.reuters.com/factcheck"),
        ("Vaccines don't contain microchips or tracking devices. Vaccine ingredients are publicly listed and verified.", "CDC Vaccine Information", "https://www.cdc.gov/vaccines/"),
        ("Vitamin C doesn't cure the common cold, though it may slightly reduce symptom duration by about 8%.", "Cochrane Reviews", "https://www.cochranelibrary.com/"),
        ("Humans use virtually all of their brain. Brain imaging shows most regions are active constantly, even during sleep.", "Neuroscience Research", "https://www.nature.com/subjects/neuroscience"),
        ("Water fluoridation reduces dental caries by 25% in children and 15% in adults. WHO endorses it as safe and effective.", "CDC Oral Health", "https://www.cdc.gov/fluoridation/"),
        ("Mobile phones don't cause brain cancer. The INTERPHONE study found no conclusive link. WHO classifies RF as possibly carcinogenic (Group 2B) but evidence is weak.", "WHO IARC Research", "https://www.iarc.who.int/"),
        ("Antibiotics only work against bacteria, not viruses. Taking them for viral infections contributes to antibiotic resistance.", "WHO Guidelines", "https://www.who.int/"),
        ("The US has the highest per capita healthcare spending at $11,945 annually, exceeding Switzerland ($9,673) and Germany ($8,176).", "OECD Health Statistics", "https://www.oecd.org/health/"),
        ("Sugar doesn't cause hyperactivity in children. Multiple controlled studies found no direct link. The myth persists due to expectancy bias.", "Pediatric Research", "https://pediatrics.aappublications.org/"),
        ("Cracking knuckles doesn't cause arthritis. The popping sound is from gas bubbles in synovial fluid, not joint damage.", "Orthopedic Research", "https://www.orthopedic.org/"),
        ("Reading in dim light doesn't permanently damage eyesight. It may cause temporary eye strain but no lasting harm.", "American Academy of Ophthalmology", "https://www.aao.org/"),
        ("Shaving doesn't make hair grow back thicker. Hair appears thicker because blunt edges feel coarser than natural tapered tips.", "American Academy of Dermatology", "https://www.aad.org/"),
        ("Moderate alcohol doesn't directly kill brain cells in healthy adults. Excessive drinking can damage brain tissue through various mechanisms.", "NIAAA", "https://www.niaaa.nih.gov/"),
        ("The human body is approximately 60% water. Water is essential for temperature regulation, nutrient transport, and waste removal.", "Medical Physiology", "https://www.nih.gov/"),
        ("Vaccines don't cause autism. This fraudulent claim has been thoroughly debunked. Extensive research found no link.", "CDC Vaccine Safety", "https://www.cdc.gov/vaccinesafety/"),
        ("Humans have five main senses plus proprioception, equilibrioception, thermoception, and nociception.", "Neuroscience Education", "https://www.brainfacts.org/"),
        ("Hand washing with soap for 20 seconds effectively prevents infection spread. Wash before eating and after using restroom.", "CDC Hand Hygiene", "https://www.cdc.gov/handwashing/"),
        ("Exercise provides cardiovascular fitness, weight management, improved mental health, and reduced chronic disease risk. WHO recommends 150 minutes weekly.", "WHO Physical Activity", "https://www.who.int/"),
        ("Adults need 7-9 hours of sleep nightly. Chronic sleep deprivation increases obesity, diabetes, and cardiovascular disease risk.", "National Sleep Foundation", "https://www.sleepfoundation.org/"),
        ("Smoking is the leading cause of preventable death, causing cancer, heart disease, stroke, and diabetes. Quitting at any age provides benefits.", "CDC Tobacco Use", "https://www.cdc.gov/tobacco/"),
        ("The Mediterranean diet reduces heart disease, stroke, type 2 diabetes, and certain cancers. It emphasizes plant-based foods and healthy fats.", "Nutrition Research", "https://www.hsph.harvard.edu/nutritionsource/"),
        ("BMI is weight (kg) divided by height (m) squared. It's useful for populations but doesn't distinguish muscle from fat.", "CDC Healthy Weight", "https://www.cdc.gov/healthyweight/"),
        ("Mental health is as important as physical health. Depression, anxiety, bipolar disorder, and schizophrenia are treatable conditions.", "National Institute of Mental Health", "https://www.nimh.nih.gov/"),
        ("Type 2 diabetes affects blood sugar regulation. Risk factors include obesity and inactivity. Often preventable through lifestyle changes.", "American Diabetes Association", "https://www.diabetes.org/"),
        ("High blood pressure (hypertension) often has no symptoms. It increases heart attack, stroke, and kidney disease risk. Normal is below 120/80.", "American Heart Association", "https://www.heart.org/"),
        ("Breast cancer is most common in women worldwide. Early detection through mammography improves survival. Treatment includes surgery, radiation, and chemotherapy.", "American Cancer Society", "https://www.cancer.org/"),
        ("Probiotics are live microorganisms providing health benefits. Found in yogurt, kefir, and sauerkraut. May help digestive and immune health.", "NCCIH", "https://www.nccih.nih.gov/"),
        ("Sunscreen protects from UV radiation causing sunburn, aging, and skin cancer. Use SPF 30+ broad-spectrum, reapply every 2 hours.", "Skin Cancer Foundation", "https://www.skincancer.org/"),
        ("The immune system protects from pathogens including bacteria, viruses, fungi, and parasites. Includes innate and adaptive responses.", "Immunology Education", "https://www.niaid.nih.gov/"),
        ("LDL ('bad') cholesterol builds up in arteries. HDL ('good') cholesterol removes cholesterol. Diet and medication manage levels.", "National Heart, Lung, Blood Institute", "https://www.nhlbi.nih.gov/"),
        ("Osteoporosis causes weak, brittle bones. Primarily affects older adults, especially postmenopausal women. Prevention includes calcium and vitamin D.", "National Osteoporosis Foundation", "https://www.nof.org/"),
        ("Asthma causes airway inflammation and breathing difficulties. Triggers include allergens, exercise, and cold air. Treatment involves bronchodilators and corticosteroids.", "American Lung Association", "https://www.lung.org/"),
        ("Alzheimer's disease is the most common dementia, affecting memory and thinking. It's progressive with no cure. Risk increases with age.", "Alzheimer's Association", "https://www.alz.org/"),
        ("The placebo effect demonstrates mind-body connection. Patients may improve from inactive treatments due to expectations.", "Medical Research", "https://www.nih.gov/"),
        ("Anesthesia allows painless surgery. General anesthesia causes unconsciousness; local numbs specific areas. Modern anesthesia is very safe.", "American Society of Anesthesiologists", "https://www.asahq.org/"),
        ("Blood types are ABO (A, B, AB, O) and Rh (+ or -). Type O negative is universal donor; AB positive is universal recipient.", "Red Cross Blood Services", "https://www.redcross.org/"),
        ("One organ donor can save up to eight lives. Organs include heart, lungs, kidneys, liver, pancreas, and intestines.", "Organ Donation", "https://www.organdonor.gov/"),
        ("The digestive system breaks down food into absorbable nutrients. Includes mouth, esophagus, stomach, intestines, liver, and pancreas. Takes 24-72 hours.", "Gastroenterology", "https://www.gi.org/"),
        ("Chronic stress negatively impacts health, causing headaches, high blood pressure, and anxiety. Management includes exercise, meditation, and sleep.", "American Psychological Association", "https://www.apa.org/"),
        ("Hormones regulate metabolism, growth, mood, and reproduction. Major hormones include insulin, thyroid hormones, cortisol, estrogen, and testosterone.", "Endocrine Society", "https://www.endocrine.org/"),
        ("The skeletal system has 206 bones in adults. It provides structure, protects organs, anchors muscles, and stores minerals.", "Anatomy Education", "https://www.anatomyexpert.com/"),
        ("CPR maintains circulation during cardiac arrest. Involves chest compressions and rescue breaths. Prompt CPR doubles or triples survival chances.", "American Heart Association", "https://www.heart.org/"),
        ("Kidney disease develops slowly with few early symptoms. Kidneys filter waste from blood. Risk factors include diabetes and high blood pressure.", "National Kidney Foundation", "https://www.kidney.org/"),
        ("Pregnancy lasts approximately 40 weeks in three trimesters. Prenatal care is essential. Important factors include nutrition and avoiding alcohol/tobacco.", "American College of Obstetricians", "https://www.acog.org/"),
    ]

    start_idx = len(evidence_list) + 1
    for i, (content, source, url) in enumerate(health_topics, start=start_idx):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "health",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    # History evidence (55 documents) - continuing numbering
    history_topics = [
        ("The Eiffel Tower was completed in March 1889 for the 1889 World's Fair in Paris. It was designed by Gustave Eiffel and stands 330 meters tall.", "Wikipedia", "https://en.wikipedia.org/wiki/Eiffel_Tower"),
        ("The Titanic sank on April 15, 1912, after hitting an iceberg on its maiden voyage. It rests at 12,500 feet depth in the North Atlantic.", "Historical Archives", "https://www.noaa.gov/"),
        ("World War II lasted from 1939 to 1945. It involved most nations and resulted in 70-85 million fatalities, making it the deadliest conflict in history.", "History Education", "https://en.wikipedia.org/wiki/World_War_II"),
        ("The Great Wall of China was built over centuries, primarily during the Ming Dynasty (1368-1644). It stretches over 13,000 miles.", "UNESCO World Heritage", "https://whc.unesco.org/"),
        ("The American Declaration of Independence was adopted on July 4, 1776, declaring independence from Great Britain.", "National Archives", "https://www.archives.gov/"),
        ("The Great Tokyo Earthquake (Kantō earthquake) struck on September 1, 1923. It killed over 140,000 people and destroyed much of Tokyo and Yokohama.", "Historical Seismic Records", "https://earthquake.usgs.gov/"),
        ("The Mona Lisa was painted by Leonardo da Vinci between 1503 and 1519 during the Italian Renaissance. It's displayed in the Louvre Museum.", "Art History", "https://www.louvre.fr/"),
        ("The Berlin Wall fell on November 9, 1989, marking the end of the Cold War era. It had divided East and West Berlin since 1961.", "Cold War History", "https://en.wikipedia.org/wiki/Berlin_Wall"),
        ("The French Revolution began in 1789 and led to the end of the monarchy, the rise of Napoleon, and profound changes in European politics.", "European History", "https://en.wikipedia.org/wiki/French_Revolution"),
        ("The Roman Empire lasted from 27 BC to 476 AD in the West and until 1453 AD in the East. It profoundly influenced Western civilization.", "Ancient History", "https://en.wikipedia.org/wiki/Roman_Empire"),
        ("Christopher Columbus reached the Americas in 1492, though Vikings had visited centuries earlier. His voyages initiated European colonization.", "World History", "https://en.wikipedia.org/wiki/Christopher_Columbus"),
        ("The printing press was invented by Johannes Gutenberg around 1440. It revolutionized information spread and contributed to the Renaissance.", "Technology History", "https://en.wikipedia.org/wiki/Printing_press"),
        ("The American Civil War (1861-1865) was fought between the Union and Confederate states over slavery and states' rights. About 620,000 soldiers died.", "US History", "https://www.nps.gov/civilwar/"),
        ("The Magna Carta was sealed in 1215, establishing the principle that the monarch is subject to law. It influenced constitutional development worldwide.", "British History", "https://www.bl.uk/magna-carta"),
        ("The Industrial Revolution began in Britain in the late 18th century, transforming economies from agrarian to industrial.", "Economic History", "https://en.wikipedia.org/wiki/Industrial_Revolution"),
        ("The Ancient Egyptian civilization lasted from approximately 3100 BC to 30 BC. It's known for pyramids, pharaohs, and hieroglyphics.", "Egyptology", "https://en.wikipedia.org/wiki/Ancient_Egypt"),
        ("The Renaissance was a cultural movement from the 14th to 17th century, beginning in Italy. It saw renewed interest in classical learning and art.", "Cultural History", "https://en.wikipedia.org/wiki/Renaissance"),
        ("The Holocaust during WWII resulted in the genocide of six million Jews and millions of others by Nazi Germany.", "Holocaust Studies", "https://www.ushmm.org/"),
        ("The Silk Road was an ancient network of trade routes connecting East and West from the 2nd century BC to the 15th century AD.", "Trade History", "https://en.wikipedia.org/wiki/Silk_Road"),
        ("The Spanish flu pandemic of 1918-1919 infected 500 million people worldwide (one-third of the population) and killed 50-100 million.", "Pandemic History", "https://www.cdc.gov/flu/pandemic-resources/"),
        ("The moon landing on July 20, 1969, saw Neil Armstrong and Buzz Aldrin become the first humans to walk on the Moon during Apollo 11.", "Space History", "https://www.nasa.gov/mission_pages/apollo/apollo11.html"),
        ("The Reformation began in 1517 when Martin Luther posted his 95 Theses, challenging Catholic Church practices and leading to Protestantism.", "Religious History", "https://en.wikipedia.org/wiki/Reformation"),
        ("The Russian Revolution of 1917 overthrew the Tsarist autocracy and led to the establishment of the Soviet Union.", "Russian History", "https://en.wikipedia.org/wiki/Russian_Revolution"),
        ("The Age of Exploration (15th-17th centuries) saw European explorers discovering new trade routes and lands, including the Americas and routes to Asia.", "Exploration History", "https://en.wikipedia.org/wiki/Age_of_Discovery"),
        ("The Great Depression began with the 1929 stock market crash and lasted through the 1930s, causing widespread unemployment and economic hardship.", "Economic History", "https://en.wikipedia.org/wiki/Great_Depression"),
        ("Ancient Greece (800 BC - 146 BC) gave birth to democracy, philosophy, drama, and the Olympic Games. Athens and Sparta were major city-states.", "Classical History", "https://en.wikipedia.org/wiki/Ancient_Greece"),
        ("The Black Death (bubonic plague) pandemic of 1347-1353 killed 75-200 million people in Eurasia and North Africa, about 30-60% of Europe's population.", "Medieval History", "https://en.wikipedia.org/wiki/Black_Death"),
        ("The Code of Hammurabi from ancient Babylon (circa 1754 BC) is one of the oldest written legal codes, featuring 282 laws.", "Legal History", "https://en.wikipedia.org/wiki/Code_of_Hammurabi"),
        ("The Crusades were religious wars between 1096 and 1291, primarily between Christians and Muslims over control of the Holy Land.", "Medieval History", "https://en.wikipedia.org/wiki/Crusades"),
        ("The Qing Dynasty ruled China from 1644 to 1912, the last imperial dynasty. It ended with the Xinhai Revolution.", "Chinese History", "https://en.wikipedia.org/wiki/Qing_dynasty"),
        ("The Treaty of Versailles ended WWI in 1919. Its harsh terms on Germany contributed to WWII. It created the League of Nations.", "WWI History", "https://en.wikipedia.org/wiki/Treaty_of_Versailles"),
        ("The Maya civilization flourished in Mesoamerica from 2000 BC to 1500 AD, known for architecture, mathematics, astronomy, and writing.", "Pre-Columbian History", "https://en.wikipedia.org/wiki/Maya_civilization"),
        ("The Boston Tea Party (December 16, 1773) was a protest against British taxation. Colonists dumped 342 chests of tea into Boston Harbor.", "American Revolution History", "https://www.bostonteapartyship.com/"),
        ("The fall of Constantinople in 1453 to the Ottoman Empire marked the end of the Byzantine Empire and is considered the end of the Middle Ages.", "Byzantine History", "https://en.wikipedia.org/wiki/Fall_of_Constantinople"),
        ("The Scramble for Africa (1881-1914) saw European powers colonize and partition Africa, with lasting impacts on the continent.", "African History", "https://en.wikipedia.org/wiki/Scramble_for_Africa"),
        ("The Napoleonic Wars (1803-1815) reshaped Europe. Napoleon's military campaigns spread revolutionary ideals but ended with his defeat at Waterloo.", "Napoleonic History", "https://en.wikipedia.org/wiki/Napoleonic_Wars"),
        ("The Aztec Empire (1428-1521) in central Mexico was conquered by Spanish conquistador Hernán Cortés. It was known for architecture and advanced society.", "Mesoamerican History", "https://en.wikipedia.org/wiki/Aztec_Empire"),
        ("The Viking Age (793-1066 AD) saw Scandinavian seafarers explore, raid, and trade across Europe, reaching North America around 1000 AD.", "Viking History", "https://en.wikipedia.org/wiki/Vikings"),
        ("The Hundred Years' War (1337-1453) between England and France shaped both nations. Joan of Arc was a key figure.", "Medieval Warfare", "https://en.wikipedia.org/wiki/Hundred_Years%27_War"),
        ("The Mongol Empire (1206-1368) was the largest contiguous land empire in history, founded by Genghis Khan.", "Asian History", "https://en.wikipedia.org/wiki/Mongol_Empire"),
        ("The partition of India in 1947 created independent India and Pakistan, accompanied by mass migration and violence killing up to 2 million.", "South Asian History", "https://en.wikipedia.org/wiki/Partition_of_India"),
        ("The Cuban Missile Crisis (October 1962) brought the US and USSR closest to nuclear war during the Cold War.", "Cold War History", "https://en.wikipedia.org/wiki/Cuban_Missile_Crisis"),
        ("The fall of the Roman Empire in 476 AD marked the end of ancient Rome. Multiple factors including invasions and economic troubles contributed.", "Ancient History", "https://en.wikipedia.org/wiki/Fall_of_the_Western_Roman_Empire"),
        ("The Watergate scandal (1972-1974) led to President Nixon's resignation. It involved illegal activities including break-ins and cover-ups.", "US Political History", "https://www.nixonlibrary.gov/"),
        ("The Women's Suffrage Movement fought for women's voting rights. The 19th Amendment gave US women the vote in 1920.", "Social History", "https://en.wikipedia.org/wiki/Women%27s_suffrage"),
        ("The Ottoman Empire (1299-1922) was a major power controlling southeastern Europe, western Asia, and northern Africa.", "Ottoman History", "https://en.wikipedia.org/wiki/Ottoman_Empire"),
        ("The Battle of Hastings (1066) saw Norman conquest of England. William the Conqueror defeated King Harold II.", "English History", "https://en.wikipedia.org/wiki/Battle_of_Hastings"),
        ("The Persian Empire (550-330 BC) under Cyrus the Great was the world's first superpower, spanning three continents.", "Ancient History", "https://en.wikipedia.org/wiki/Achaemenid_Empire"),
        ("The Meiji Restoration (1868) transformed Japan from a feudal society to a modern industrialized nation in just decades.", "Japanese History", "https://en.wikipedia.org/wiki/Meiji_Restoration"),
        ("The Wars of the Roses (1455-1487) were English civil wars between Houses of Lancaster and York. They ended with Henry Tudor's victory.", "English History", "https://en.wikipedia.org/wiki/Wars_of_the_Roses"),
        ("The Louisiana Purchase (1803) doubled US territory. America bought 828,000 square miles from France for $15 million.", "US Expansion History", "https://en.wikipedia.org/wiki/Louisiana_Purchase"),
        ("The Irish Potato Famine (1845-1852) killed about 1 million and caused 1 million to emigrate. It profoundly affected Irish history.", "Irish History", "https://en.wikipedia.org/wiki/Great_Famine_(Ireland)"),
        ("Nelson Mandela fought against apartheid in South Africa. He was imprisoned 27 years, then became president (1994-1999).", "African History", "https://en.wikipedia.org/wiki/Nelson_Mandela"),
        ("The Suez Crisis (1956) involved Egypt, Israel, UK, and France. It marked the end of British and French dominance in the Middle East.", "Middle East History", "https://en.wikipedia.org/wiki/Suez_Crisis"),
        ("The invention of gunpowder in 9th century China revolutionized warfare. It spread to Europe by the 13th century.", "Military History", "https://en.wikipedia.org/wiki/Gunpowder"),
    ]

    start_idx = len(evidence_list) + 1
    for i, (content, source, url) in enumerate(history_topics, start=start_idx):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "history",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    # Technology evidence (45 documents)
    technology_topics = [
        ("Python programming language was created by Guido van Rossum. First released in 1991, it emphasizes code readability and simplicity.", "Python.org", "https://www.python.org/"),
        ("The Internet originated from ARPANET in the late 1960s. TCP/IP protocols were adopted in 1983, and the World Wide Web was invented by Tim Berners-Lee in 1989.", "Internet History", "https://www.internetsociety.org/"),
        ("Tim Berners-Lee invented the World Wide Web (WWW) in 1989 while working at CERN. He created HTTP, HTML, and the first web browser.", "CERN", "https://home.cern/"),
        ("Smartphones use significantly more electricity than traditional phones due to processing power, large displays, and wireless connectivity.", "Energy Studies", "https://www.energy.gov/"),
        ("The first transatlantic telegraph cable was successfully laid in 1858, connecting Ireland and Newfoundland. It revolutionized international communication.", "Technology History", "https://www.britannica.com/"),
        ("Artificial intelligence can pass the Turing Test. Modern language models can successfully fool evaluators in conversational scenarios.", "AI Research", "https://www.turing.org.uk/"),
        ("The transistor was invented at Bell Labs in 1947. It revolutionized electronics and led to modern computing.", "Electronics History", "https://en.wikipedia.org/wiki/Transistor"),
        ("The first electronic computer, ENIAC, was completed in 1945. It weighed 30 tons and occupied 1,800 square feet.", "Computing History", "https://en.wikipedia.org/wiki/ENIAC"),
        ("The microprocessor, invented by Intel in 1971, integrated all CPU functions onto a single chip, enabling personal computers.", "Computer Architecture", "https://www.intel.com/"),
        ("Email was invented by Ray Tomlinson in 1971. He sent the first network email and chose the @ symbol for addresses.", "Internet History", "https://en.wikipedia.org/wiki/Email"),
        ("GPS (Global Positioning System) was developed by the US military and made available for civilian use in 1983. It uses 24+ satellites.", "Navigation Technology", "https://www.gps.gov/"),
        ("The first iPhone was released by Apple in 2007, revolutionizing mobile phones by combining phone, internet, and music player.", "Mobile Technology", "https://www.apple.com/"),
        ("Blockchain technology underlies cryptocurrencies like Bitcoin. It provides a decentralized, secure ledger for transactions.", "Cryptography", "https://en.wikipedia.org/wiki/Blockchain"),
        ("Cloud computing delivers computing services over the internet. Major providers include AWS, Microsoft Azure, and Google Cloud.", "Cloud Technology", "https://aws.amazon.com/"),
        ("Machine learning is a subset of AI where computers learn from data without explicit programming. Applications include image recognition and natural language processing.", "AI/ML", "https://www.tensorflow.org/"),
        ("Fiber optic cables transmit data as light pulses through glass fibers. They enable high-speed internet with speeds up to terabits per second.", "Telecommunications", "https://en.wikipedia.org/wiki/Fiber-optic_cable"),
        ("Quantum computing uses quantum bits (qubits) that can exist in multiple states simultaneously. It promises to solve problems intractable for classical computers.", "Quantum Computing", "https://www.ibm.com/quantum-computing/"),
        ("The Ethernet networking standard was developed by Robert Metcalfe at Xerox PARC in 1973. It remains the dominant LAN technology.", "Networking", "https://en.wikipedia.org/wiki/Ethernet"),
        ("USB (Universal Serial Bus) was introduced in 1996 to standardize computer peripherals. USB-C is the latest standard supporting high-speed data and power.", "Computer Interfaces", "https://www.usb.org/"),
        ("Virtual reality (VR) creates immersive digital environments. Modern VR headsets provide realistic graphics and motion tracking for gaming and training.", "VR Technology", "https://en.wikipedia.org/wiki/Virtual_reality"),
        ("3D printing (additive manufacturing) builds objects layer by layer from digital models. Applications span prototyping, manufacturing, and medicine.", "Manufacturing", "https://en.wikipedia.org/wiki/3D_printing"),
        ("Autonomous vehicles use sensors, cameras, and AI to navigate without human control. Major companies are developing self-driving car technology.", "Transportation Technology", "https://en.wikipedia.org/wiki/Self-driving_car"),
        ("The World Wide Web Consortium (W3C) develops web standards including HTML, CSS, and XML to ensure interoperability.", "Web Standards", "https://www.w3.org/"),
        ("Open source software has publicly available source code. Linux, Apache, and Firefox are prominent examples. It promotes collaboration and transparency.", "Software Development", "https://opensource.org/"),
        ("Encryption protects data by encoding it so only authorized parties can access it. Modern encryption uses complex mathematical algorithms.", "Cybersecurity", "https://en.wikipedia.org/wiki/Encryption"),
        ("The Internet of Things (IoT) connects everyday devices to the internet. Applications include smart homes, wearables, and industrial sensors.", "IoT", "https://en.wikipedia.org/wiki/Internet_of_things"),
        ("Solid-state drives (SSDs) use flash memory instead of spinning disks. They're faster, more durable, and energy-efficient than hard disk drives.", "Storage Technology", "https://en.wikipedia.org/wiki/Solid-state_drive"),
        ("5G networks provide faster speeds, lower latency, and support more connected devices than 4G. Deployment began globally around 2019.", "Wireless Technology", "https://www.gsma.com/futurenetworks/5g/"),
        ("Linux is an open-source operating system kernel created by Linus Torvalds in 1991. It powers most servers and Android devices.", "Operating Systems", "https://www.linux.org/"),
        ("Biometric authentication uses unique physical characteristics like fingerprints, facial recognition, or iris scans for security.", "Security Technology", "https://en.wikipedia.org/wiki/Biometrics"),
        ("Augmented reality (AR) overlays digital information onto the real world. Applications include mobile games, navigation, and industrial training.", "AR Technology", "https://en.wikipedia.org/wiki/Augmented_reality"),
        ("The Raspberry Pi is a low-cost single-board computer launched in 2012. It's used for education, prototyping, and DIY projects.", "Educational Technology", "https://www.raspberrypi.org/"),
        ("Git is a distributed version control system created by Linus Torvalds in 2005. GitHub and GitLab are popular hosting platforms.", "Software Development", "https://git-scm.com/"),
        ("Docker containers package software with dependencies for consistent deployment across environments. It revolutionized application deployment.", "DevOps", "https://www.docker.com/"),
        ("Natural language processing (NLP) enables computers to understand and generate human language. Applications include chatbots and translation.", "AI/NLP", "https://en.wikipedia.org/wiki/Natural_language_processing"),
        ("Wi-Fi provides wireless local area networking based on IEEE 802.11 standards. Wi-Fi 6 is the latest generation offering improved speed and capacity.", "Wireless Technology", "https://www.wi-fi.org/"),
        ("Cryptocurrency is digital currency using cryptography for security. Bitcoin, created in 2009, was the first decentralized cryptocurrency.", "Financial Technology", "https://en.wikipedia.org/wiki/Cryptocurrency"),
        ("API (Application Programming Interface) allows different software applications to communicate. RESTful APIs are common for web services.", "Software Architecture", "https://en.wikipedia.org/wiki/API"),
        ("Serverless computing allows developers to build applications without managing servers. Cloud providers handle infrastructure automatically.", "Cloud Computing", "https://en.wikipedia.org/wiki/Serverless_computing"),
        ("Edge computing processes data near the source rather than in centralized data centers, reducing latency for IoT and real-time applications.", "Distributed Computing", "https://en.wikipedia.org/wiki/Edge_computing"),
        ("Big data refers to extremely large datasets analyzed computationally to reveal patterns and trends. Technologies include Hadoop and Spark.", "Data Science", "https://en.wikipedia.org/wiki/Big_data"),
        ("DevOps combines software development and IT operations to shorten development cycles and provide continuous delivery.", "Software Engineering", "https://en.wikipedia.org/wiki/DevOps"),
        ("Kubernetes is an open-source container orchestration platform for automating deployment, scaling, and management of containerized applications.", "Cloud Native", "https://kubernetes.io/"),
        ("Microservices architecture structures applications as collections of loosely coupled services, improving modularity and scalability.", "Software Architecture", "https://en.wikipedia.org/wiki/Microservices"),
        ("Deep learning uses neural networks with multiple layers to learn from data. It powers image recognition, speech recognition, and autonomous vehicles.", "Machine Learning", "https://en.wikipedia.org/wiki/Deep_learning"),
    ]

    start_idx = len(evidence_list) + 1
    for i, (content, source, url) in enumerate(technology_topics, start=start_idx):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "technology",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    # Politics evidence (25 documents)
    politics_topics = [
        ("Donald Trump was elected the 45th US President in 2016, defeating Hillary Clinton. He served from 2017 to 2021.", "Electoral Records", "https://www.fec.gov/"),
        ("Joe Biden is the 46th President of the United States. He was inaugurated on January 20, 2021, after defeating Donald Trump in 2020.", "Whitehouse.gov", "https://www.whitehouse.gov/"),
        ("The United States Electoral College system has 538 electors. A candidate needs 270 electoral votes to win the presidency.", "US Constitution", "https://www.archives.gov/"),
        ("The United Nations was founded in 1945 after WWII. It has 193 member states and aims to maintain international peace and security.", "United Nations", "https://www.un.org/"),
        ("The European Union was established by the Maastricht Treaty in 1993. It has 27 member states after the UK's departure (Brexit) in 2020.", "European Union", "https://europa.eu/"),
        ("The US Constitution was ratified in 1788. It established the framework of the US government with three branches: executive, legislative, and judicial.", "National Archives", "https://www.archives.gov/founding-docs/constitution"),
        ("The US Supreme Court has nine justices appointed for life. It's the highest judicial authority in the United States.", "Supreme Court", "https://www.supremecourt.gov/"),
        ("NATO (North Atlantic Treaty Organization) was founded in 1949 as a military alliance. It has 31 member countries as of 2023.", "NATO", "https://www.nato.int/"),
        ("The UN Security Council has 15 members, including 5 permanent members (US, UK, France, Russia, China) with veto power.", "United Nations", "https://www.un.org/securitycouncil/"),
        ("The Watergate scandal led to President Richard Nixon's resignation in 1974. It involved break-ins and cover-ups of illegal activities.", "US History", "https://www.nixonlibrary.gov/"),
        ("The Civil Rights Act of 1964 outlawed discrimination based on race, color, religion, sex, or national origin in the United States.", "Civil Rights", "https://www.archives.gov/"),
        ("The Voting Rights Act of 1965 prohibited racial discrimination in voting, particularly affecting Southern states.", "Voting Rights", "https://www.justice.gov/"),
        ("The Affordable Care Act (Obamacare) was signed into law in 2010, expanding health insurance coverage to millions of Americans.", "Healthcare Policy", "https://www.healthcare.gov/"),
        ("The US Congress consists of two chambers: the Senate (100 members) and the House of Representatives (435 members).", "US Government", "https://www.congress.gov/"),
        ("Impeachment is the process by which a legislature brings charges against a government official. The House impeaches; the Senate tries the case.", "Constitutional Law", "https://www.senate.gov/"),
        ("The 22nd Amendment limits US presidents to two terms in office. It was ratified in 1951 after Franklin Roosevelt's four terms.", "Constitutional Amendments", "https://www.archives.gov/"),
        ("The US federal government operates on a system of checks and balances among executive, legislative, and judicial branches.", "Civics", "https://www.usa.gov/"),
        ("Parliamentary systems feature a prime minister as head of government, chosen by the legislature. Examples include the UK, Canada, and India.", "Political Systems", "https://en.wikipedia.org/wiki/Parliamentary_system"),
        ("The Universal Declaration of Human Rights was adopted by the UN in 1948. It outlines fundamental human rights to be universally protected.", "Human Rights", "https://www.un.org/en/about-us/universal-declaration-of-human-rights"),
        ("Lobbying involves attempting to influence government decisions. Lobbyists represent various interests including corporations, unions, and advocacy groups.", "Political Process", "https://en.wikipedia.org/wiki/Lobbying"),
        ("Gerrymandering is the manipulation of electoral district boundaries to favor one party. It's a controversial practice affecting fair representation.", "Electoral Politics", "https://en.wikipedia.org/wiki/Gerrymandering"),
        ("The separation of powers divides government into distinct branches with separate functions to prevent concentration of power.", "Political Theory", "https://en.wikipedia.org/wiki/Separation_of_powers"),
        ("A filibuster is a tactic used in the US Senate to delay or block legislative action by extending debate indefinitely.", "Senate Procedures", "https://www.senate.gov/"),
        ("The G7 is a group of seven major advanced economies: Canada, France, Germany, Italy, Japan, UK, and US. They meet annually to discuss global issues.", "International Relations", "https://en.wikipedia.org/wiki/G7"),
        ("Term limits restrict the number of terms an elected official can serve. The US president is limited to two terms; many state governors have term limits.", "Electoral Systems", "https://en.wikipedia.org/wiki/Term_limit"),
    ]

    start_idx = len(evidence_list) + 1
    for i, (content, source, url) in enumerate(politics_topics, start=start_idx):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "politics",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    # Geography evidence (25 documents)
    geography_topics = [
        ("Mount Everest is the world's highest mountain at 8,849 meters (29,032 feet) above sea level, located in the Himalayas on the Nepal-China border.", "Geography", "https://en.wikipedia.org/wiki/Mount_Everest"),
        ("The Amazon River is the world's largest river by discharge volume and the second longest after the Nile. It flows through South America.", "Geography", "https://en.wikipedia.org/wiki/Amazon_River"),
        ("The Sahara Desert is the world's largest hot desert, covering 9 million square kilometers across North Africa.", "Geography", "https://en.wikipedia.org/wiki/Sahara"),
        ("Russia is the world's largest country by land area at 17.1 million km². It spans 11 time zones across Europe and Asia.", "World Geography", "https://en.wikipedia.org/wiki/Russia"),
        ("The Pacific Ocean is the largest and deepest ocean, covering more than 63 million square miles (165 million km²).", "Oceanography", "https://en.wikipedia.org/wiki/Pacific_Ocean"),
        ("The Mariana Trench is the deepest point in Earth's oceans at approximately 36,000 feet (11,000 meters) below sea level.", "Oceanography", "https://www.noaa.gov/"),
        ("The Nile River is traditionally considered the world's longest river at approximately 6,650 km (4,130 miles), flowing through northeastern Africa.", "Geography", "https://en.wikipedia.org/wiki/Nile"),
        ("Antarctica is the world's fifth-largest continent and the coldest, driest, and windiest. It contains 70% of Earth's fresh water as ice.", "Antarctic Geography", "https://en.wikipedia.org/wiki/Antarctica"),
        ("The Grand Canyon in Arizona is 277 miles long, up to 18 miles wide, and over 1 mile deep. It was carved by the Colorado River.", "US Geography", "https://www.nps.gov/grca/"),
        ("The Great Barrier Reef off Australia's coast is the world's largest coral reef system, stretching over 2,300 kilometers.", "Marine Geography", "https://en.wikipedia.org/wiki/Great_Barrier_Reef"),
        ("The Ring of Fire is a major area in the Pacific Ocean basin where many earthquakes and volcanic eruptions occur, containing 75% of active volcanoes.", "Geology", "https://en.wikipedia.org/wiki/Ring_of_Fire"),
        ("The Dead Sea between Israel and Jordan is Earth's lowest land elevation at 430 meters below sea level. It's one of the saltiest bodies of water.", "Geography", "https://en.wikipedia.org/wiki/Dead_Sea"),
        ("Vatican City is the world's smallest country at 0.17 square miles (0.44 km²), located within Rome, Italy.", "World Geography", "https://en.wikipedia.org/wiki/Vatican_City"),
        ("China is the world's most populous country with over 1.4 billion people, followed by India with a similar population.", "Demographics", "https://www.un.org/development/desa/pd/"),
        ("The Himalayas are the world's highest mountain range, formed by the collision of Indian and Eurasian tectonic plates.", "Physical Geography", "https://en.wikipedia.org/wiki/Himalayas"),
        ("Australia is both a country and a continent, the world's sixth-largest country by total area at 7.7 million km².", "World Geography", "https://en.wikipedia.org/wiki/Australia"),
        ("The Mediterranean Sea connects to the Atlantic Ocean through the Strait of Gibraltar. It borders 21 countries across three continents.", "Physical Geography", "https://en.wikipedia.org/wiki/Mediterranean_Sea"),
        ("The Andes are the world's longest continental mountain range, extending 7,000 km along South America's western coast.", "Physical Geography", "https://en.wikipedia.org/wiki/Andes"),
        ("Lake Baikal in Siberia is the world's deepest and oldest freshwater lake, containing 20% of the world's unfrozen freshwater.", "Limnology", "https://en.wikipedia.org/wiki/Lake_Baikal"),
        ("The equator divides Earth into Northern and Southern Hemispheres. It passes through 13 countries with a length of 40,075 km.", "Physical Geography", "https://en.wikipedia.org/wiki/Equator"),
        ("Greenland is the world's largest island at 2.16 million km², located between the Arctic and Atlantic Oceans. Most of it is covered by ice.", "Geography", "https://en.wikipedia.org/wiki/Greenland"),
        ("The Congo River is the world's deepest river and Africa's second-longest. It's the only major river crossing the equator twice.", "African Geography", "https://en.wikipedia.org/wiki/Congo_River"),
        ("Tokyo is the world's most populous metropolitan area with over 37 million people in the greater Tokyo area.", "Urban Geography", "https://en.wikipedia.org/wiki/Tokyo"),
        ("The Alps are Europe's highest and most extensive mountain range, stretching across eight countries with 82 peaks above 4,000 meters.", "European Geography", "https://en.wikipedia.org/wiki/Alps"),
        ("The Panama Canal connects the Atlantic and Pacific Oceans through the Isthmus of Panama. It opened in 1914 and revolutionized maritime trade.", "Economic Geography", "https://en.wikipedia.org/wiki/Panama_Canal"),
    ]

    start_idx = len(evidence_list) + 1
    for i, (content, source, url) in enumerate(geography_topics, start=start_idx):
        evidence_list.append({
            "id": f"sample_ev_{i:03d}",
            "content": content,
            "source": source,
            "url": url,
            "category": "geography",
            "relevance": "high",
            "language": "en",
            "date_added": "2025-10-29"
        })

    return evidence_list


def calculate_statistics(evidence_list):
    """Calculate corpus statistics."""
    category_counts = {}
    total_length = 0
    lengths = []

    for item in evidence_list:
        category = item['category']
        category_counts[category] = category_counts.get(category, 0) + 1
        length = len(item['content'])
        lengths.append(length)
        total_length += length

    return {
        "total_items": len(evidence_list),
        "categories": category_counts,
        "avg_length": total_length // len(evidence_list) if evidence_list else 0,
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0
    }


def save_json(evidence_list, output_path):
    """Save evidence corpus as JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evidence_list, f, indent=2, ensure_ascii=False)
    print(f"Created JSON corpus: {output_path}")


def save_csv(evidence_list, output_path):
    """Save evidence corpus as CSV."""
    fieldnames = ['id', 'content', 'source', 'url', 'category', 'relevance', 'language', 'date_added']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evidence_list)
    print(f"Created CSV corpus: {output_path}")


def save_metadata(stats, output_path):
    """Save corpus metadata."""
    metadata = {
        "name": "TruthGraph Sample Evidence Corpus",
        "version": "1.0",
        "date_created": "2025-10-29",
        "total_items": stats["total_items"],
        "categories": stats["categories"],
        "sources": ["Wikipedia", "CDC", "WHO", "NASA", "NIST", "NOAA", "NIH", "Various Educational Sources"],
        "languages": ["en"],
        "statistics": {
            "avg_length": stats["avg_length"],
            "min_length": stats["min_length"],
            "max_length": stats["max_length"]
        },
        "description": "Comprehensive evidence corpus for TruthGraph testing and demonstrations, covering science, health, history, technology, politics, and geography."
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Created metadata: {output_path}")


def main():
    """Main function to generate evidence corpus."""
    output_dir = Path("c:/repos/truthgraph/data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating TruthGraph Sample Evidence Corpus...")
    print("=" * 60)

    # Generate evidence
    evidence_list = generate_corpus()
    print(f"\nGenerated {len(evidence_list)} evidence documents")

    # Calculate statistics
    stats = calculate_statistics(evidence_list)
    print(f"\nCategory breakdown:")
    for category, count in sorted(stats["categories"].items()):
        percentage = (count / stats["total_items"]) * 100
        print(f"  {category:12s}: {count:3d} documents ({percentage:5.1f}%)")

    print(f"\nContent statistics:")
    print(f"  Average length: {stats['avg_length']} characters")
    print(f"  Min length: {stats['min_length']} characters")
    print(f"  Max length: {stats['max_length']} characters")

    # Save files
    print(f"\nSaving files to {output_dir}...")
    save_json(evidence_list, output_dir / "evidence_corpus.json")
    save_csv(evidence_list, output_dir / "evidence_corpus.csv")
    save_metadata(stats, output_dir / "metadata.json")

    print("\n" + "=" * 60)
    print("✓ Evidence corpus generation complete!")
    print(f"✓ Total documents: {stats['total_items']}")
    print(f"✓ Files created in: {output_dir}")


if __name__ == "__main__":
    main()

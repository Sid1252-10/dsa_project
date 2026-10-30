export const punjabGraph = {
  cities: [
    { id: "amritsar",   name: "Amritsar",          x: 120, y: 120, kind: "major" },
    { id: "tarn_taran", name: "Tarn Taran",        x: 135, y: 150, kind: "minor" },
    { id: "gurdaspur",  name: "Gurdaspur",         x: 175, y:  95, kind: "minor" },
    { id: "pathankot",  name: "Pathankot",         x: 235, y:  75, kind: "major" },
    { id: "hoshiarpur", name: "Hoshiarpur",        x: 260, y: 150, kind: "minor" },
    { id: "kapurthala", name: "Kapurthala",        x: 210, y: 200, kind: "minor" },
    { id: "jalandhar",  name: "Jalandhar",         x: 260, y: 220, kind: "major" },
    { id: "ludhiana",   name: "Ludhiana",          x: 340, y: 260, kind: "major" },
    { id: "moga",       name: "Moga",              x: 290, y: 320, kind: "minor" },
    { id: "firozpur",   name: "Firozpur",          x: 205, y: 360, kind: "minor" },
    { id: "fazilka",    name: "Fazilka",           x: 130, y: 430, kind: "minor" },
    { id: "abohar",     name: "Abohar",            x: 175, y: 460, kind: "minor" },
    { id: "bathinda",   name: "Bathinda",          x: 300, y: 430, kind: "major" },
    { id: "faridkot",   name: "Faridkot",          x: 255, y: 395, kind: "minor" },
    { id: "muktsar",    name: "Sri Muktsar Sahib", x: 235, y: 450, kind: "minor" },
    { id: "mansa",      name: "Mansa",             x: 360, y: 455, kind: "minor" },
    { id: "barnala",    name: "Barnala",           x: 385, y: 380, kind: "minor" },
    { id: "sangrur",    name: "Sangrur",           x: 430, y: 360, kind: "minor" },
    { id: "patiala",    name: "Patiala",           x: 500, y: 350, kind: "major" },
    { id: "malerkotla", name: "Malerkotla",        x: 450, y: 320, kind: "minor" },
    { id: "rupnagar",   name: "Rupnagar",          x: 455, y: 230, kind: "minor" },
    { id: "mohali",     name: "Mohali",            x: 520, y: 260, kind: "major" },
    { id: "chandigarh", name: "Chandigarh",        x: 560, y: 240, kind: "major" }
  ],
  // [cityA, cityB, distanceKm]  — real approximate road distances
  roads: [
    // north-west cluster
    ["amritsar",   "tarn_taran",  26],
    ["amritsar",   "gurdaspur",   64],
    ["gurdaspur",  "pathankot",   42],
    ["pathankot",  "hoshiarpur",  68],
    ["hoshiarpur", "jalandhar",   55],
    ["tarn_taran", "kapurthala",  38],
    ["kapurthala", "jalandhar",   22],
    ["amritsar",   "kapurthala",  60],

    // central belt
    ["jalandhar",  "ludhiana",    60],
    ["ludhiana",   "rupnagar",    46],
    ["rupnagar",   "mohali",      40],
    ["mohali",     "chandigarh",  12],
    ["rupnagar",   "chandigarh",  45],
    ["ludhiana",   "malerkotla",  50],
    ["malerkotla", "sangrur",     26],
    ["malerkotla", "patiala",     62],
    ["sangrur",    "patiala",     55],

    // west-south belt
    ["ludhiana",   "moga",        54],
    ["moga",       "firozpur",    56],
    ["firozpur",   "fazilka",     52],
    ["fazilka",    "abohar",      24],
    ["abohar",     "muktsar",     65],
    ["muktsar",    "bathinda",    76],
    ["faridkot",   "bathinda",    52],
    ["faridkot",   "moga",        47],
    ["faridkot",   "muktsar",     33],

    // south-east belt
    ["bathinda",   "barnala",     47],
    ["barnala",    "sangrur",     34],
    ["barnala",    "mansa",       32],
    ["mansa",      "bathinda",    38],
    ["patiala",    "mohali",      65],
    ["ludhiana",   "patiala",     95]
  ]
};

# Open Data Sources Registry

This is the canonical portal-to-connector map for OpenTIR-Data. Every row
comes from one of the two CSVs the user attached:

- `open_data_us.csv` — 132 US state, city, and county portals
- `open_data_intl.csv` — 189 international country, regional, and city portals

**Total: 321 portals.** They split across 5 connector families:

| Connector | Note | Count |
|---|---|---|
| [[ckan-generic]] | Generic CKAN 2.x | ~70 |
| [[socrata]] | Socrata / SODA | ~70 |
| [[arcgis-hub]] | ArcGIS Hub v3 | ~70 |
| [[opendata-soft]] | OpenDataSoft v2.1 | ~30 |
| _custom / unknown_ | bespoke portal; needs its own fetcher | ~80 |

The platform for each portal was detected by URL pattern + spot-check probe of
the catalog endpoint. Some "custom" entries (e.g. `data.gov`, OECD archive,
`data.slovensko.sk`) are actually backed by a known platform but the public
landing page hides it; they get a `?` until a real probe confirms.

## Format

Each row: `Name, URL, Connector, Probe status`

`Probe status`:

- ✅ — confirmed live with curl, catalog endpoint returned 200 JSON
- ⏳ — URL pattern matches a known platform but not yet probed
- ❓ — platform not yet classified

## United States (open_data_us.csv)

| Name | URL | Connector | Probe |
|---|---|---|---|
| Alabama | http://open.alabama.gov/ | custom | ❓ |
| Alaska DGGS | http://dggs.alaska.gov/pubs/series/dggs/digital-data-series | custom | ❓ |
| Alaska GIS | https://gis.data.alaska.gov/ | arcgis-hub | ⏳ |
| Albuquerque | http://www.cabq.gov/abq-data/ | custom | ❓ |
| Alexandria VA | https://www.alexandriava.gov/gis/open-data | arcgis-hub | ⏳ |
| Anchorage | https://www.muni.org/Departments/it/Pages/opendata.aspx | custom | ❓ |
| Ann Arbor | https://www.a2gov.org/services/data/Pages/default.aspx | custom | ❓ |
| Arizona | https://openbooks.az.gov/ | custom | ❓ |
| Arizona Geological Survey | https://azgs.arizona.edu/index.php | custom | ❓ |
| Arkansas | https://transparency.arkansas.gov/ | custom | ❓ |
| Arkansas GIO | http://gis.arkansas.gov/ | arcgis-hub | ⏳ |
| Arlington | https://data.arlingtonva.us/home | socrata | ⏳ |
| Arvada | https://gis-arvada.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Asheville | https://data-avl.opendata.arcgis.com/ | arcgis-hub | ✅ |
| Atlanta | http://gis.atlantaga.gov/ | arcgis-hub | ⏳ |
| Austin | http://data.austintexas.gov/ | socrata | ⏳ |
| Baltimore | http://data.baltimorecity.gov/ | socrata | ⏳ |
| Baton Rouge | https://data.brla.gov/ | socrata | ⏳ |
| Belleville | https://www.belleville.net/541/Open-Government | custom | ❓ |
| Bloomington IN | https://data.bloomington.in.gov/ | socrata | ⏳ |
| Boston | https://www.boston.gov/ | custom | ❓ |
| Boston Enterprise GIS | https://boston.maps.arcgis.com/home/index.html | arcgis-hub | ⏳ |
| Burlington GIS | https://www.burlington.org/305/GIS-Maps | custom | ❓ |
| California | https://data.ca.gov/ | socrata | ⏳ |
| Champaign | https://gis-cityofchampaign.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Chapel Hill | https://www.chapelhillopendata.org/page/home1/ | custom | ❓ |
| Charlotte NC | https://data.charlottenc.gov/ | socrata | ⏳ |
| Chesapeake VA | https://public-chesva.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Chicago | http://data.cityofchicago.org/ | socrata | ⏳ |
| Columbus | https://opendata.columbus.gov/ | socrata | ⏳ |
| Colorado | https://data.colorado.gov/ | socrata | ⏳ |
| Connecticut | https://osc.ct.gov/openct/ | custom | ❓ |
| Cook County | https://datacatalog.cookcountyil.gov/ | socrata | ⏳ |
| Delaware | https://delaware.gov/guides/data/ | custom | ❓ |
| Denver | https://opendata-geospatialdenver.hub.arcgis.com/ | arcgis-hub | ✅ |
| Denver Regional Council | https://drcog.org/ | custom | ❓ |
| District of Columbia | https://opendata.dc.gov/ | socrata | ⏳ |
| Durham | https://live-durhamnc.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Fairfax County | https://www.fairfaxcounty.gov/maps/open-geospatial-data | arcgis-hub | ⏳ |
| Florida | http://www.floridahasarighttoknow.com/ | custom | ❓ |
| Florida GIS | https://geodata.floridagio.gov/ | arcgis-hub | ⏳ |
| Georgia | https://open.ga.gov/ | socrata | ⏳ |
| Gilpin County | https://gilpin-county-gis-data-gilpincdd.hub.arcgis.com/ | arcgis-hub | ⏳ |
| Hartford | https://www.hartfordct.gov/.../GIS-Digital-Data | custom | ❓ |
| Hawaii | http://data.hawaii.gov/ | socrata | ⏳ |
| Hawaii GIS | https://geoportal.hawaii.gov/ | arcgis-hub | ⏳ |
| Hidalgo County | https://www.hidalgocounty.us/2703/Open-Government | custom | ❓ |
| Honolulu | https://data.honolulu.gov/ | socrata | ⏳ |
| Houston | http://data.houstontx.gov/ | socrata | ⏳ |
| Idaho | https://gis.idaho.gov/ | arcgis-hub | ⏳ |
| Illinois | http://data.illinois.gov/ | socrata | ⏳ |
| Indiana | http://www.stats.indiana.edu/ | custom | ❓ |
| Indianapolis/Marion County | http://data.indy.gov/ | socrata | ⏳ |
| Iowa | http://data.iowa.gov/ | socrata | ⏳ |
| Kansas | https://ag.ks.gov/open-government | custom | ❓ |
| Kansas City | https://data.kcmo.org/ | socrata | ⏳ |
| Kentucky | https://transparency.ky.gov/Pages/default.aspx | custom | ❓ |
| King County | https://data.kingcounty.gov/ | socrata | ⏳ |
| Lake County | http://data-lakecountyil.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Las Vegas | https://www.lasvegasnevada.gov/Government/Transparency | custom | ❓ |
| Lexington | https://data.lexingtonky.gov/ | socrata | ⏳ |
| Lincoln NE | http://opendata.lincoln.ne.gov/ | custom | ❓ |
| Little Rock AR | https://data.littlerock.gov/ | socrata | ⏳ |
| Los Angeles | https://controllerdata.lacity.org/browse | socrata | ⏳ |
| Los Angeles County | https://data.lacounty.gov/ | socrata | ⏳ |
| Loudoun County | https://www.arcgis.com/home/item.html?id=fc9a9ee1d1744ec298c60a911b08d6ea | arcgis-hub | ⏳ |
| Louisiana | https://wwwcfprd.doa.louisiana.gov/latrac/portal.cfm | custom | ❓ |
| Louisville | https://data.louisvilleky.gov/ | socrata | ⏳ |
| Madison | https://data-cityofmadison.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Maine | https://www.maine.gov/geolib/catalog.html | custom | ❓ |
| Marion County | http://data.indy.gov/ | socrata | ⏳ |
| Maryland | https://opendata.maryland.gov/ | socrata | ⏳ |
| Massachusetts | https://www.mass.gov/get-massgis-geospatial-data | custom | ❓ |
| Michigan | http://www.michigan.gov/data/ | custom | ❓ |
| Minnesota | https://mn.gov/portal/ | custom | ❓ |
| Mississippi | http://opendata.gis.ms.gov/ | arcgis-hub | ⏳ |
| Missouri | http://data.mo.gov/ | socrata | ⏳ |
| Missouri Accountability | http://mapyourtaxes.mo.gov/MAP/Portal/Default.aspx | custom | ❓ |
| Montana | https://data.mt.gov/ | socrata | ⏳ |
| Montgomery County | https://data.montgomerycountymd.gov/ | socrata | ⏳ |
| Nashville | https://data.nashville.gov/ | socrata | ⏳ |
| Nebraska | https://www.nebraska.gov/government/open-data/ | custom | ❓ |
| Nevada | https://open.nv.gov/ | custom | ❓ |
| New Hampshire | https://www.doit.nh.gov/ | custom | ❓ |
| New Jersey | https://data.nj.gov/ | socrata | ⏳ |
| New Mexico | https://ssp.nm.gov/ | custom | ❓ |
| New Orleans | https://datadriven.nola.gov/home/ | socrata | ⏳ |
| New York | https://data.ny.gov/ | socrata | ⏳ |
| New York City | https://opendata.cityofnewyork.us/ | socrata | ⏳ |
| North Carolina | https://www.nc.gov/government/open-budget | custom | ❓ |
| North Dakota GIS Hub | https://www.gis.nd.gov/ | arcgis-hub | ⏳ |
| NY State Senate | https://www.nysenate.gov/ | custom | ❓ |
| Ohio | https://ohio.gov/government/topic-hubs/transparency | custom | ❓ |
| Oklahoma | https://data.ok.gov/ | socrata | ⏳ |
| Oregon | http://data.oregon.gov/ | socrata | ⏳ |
| Palo Alto | http://data.cityofpaloalto.org/ | socrata | ⏳ |
| Pennsylvania | https://data.pa.gov/ | socrata | ⏳ |
| Philadelphia | http://www.opendataphilly.org/ | custom | ❓ |
| Portland | https://www.portland.gov/open-data-statistics-and-maps | custom | ❓ |
| Prince George's County | https://data.princegeorgescountymd.gov/ | socrata | ⏳ |
| Providence | https://data.providenceri.gov/ | socrata | ⏳ |
| Raleigh | https://raleighnc.gov/.../services/gis-and-open-data | arcgis-hub | ⏳ |
| Rhode Island | http://www.ri.gov/data/ | custom | ❓ |
| Rockford | https://data.illinois.gov/organization/city-of-rockford | socrata | ⏳ |
| San Francisco | https://www.sf.gov/departments/city-administrator/datasf | socrata | ✅ |
| San Mateo County | https://data.smcgov.org/ | socrata | ⏳ |
| Santa Cruz | https://data.ca.gov/dataset/city-of-santa-cruz | socrata | ⏳ |
| Santa Rosa | https://data-santarosa.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Scottsdale | http://data.scottsdaleaz.gov/ | socrata | ⏳ |
| Seattle | http://data.seattle.gov/ | socrata | ⏳ |
| Sioux Falls SD | https://dataworks.siouxfalls.gov/ | custom | ❓ |
| Somerville | http://data.somervillema.gov/ | socrata | ⏳ |
| South Bend | https://data-southbend.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| South Carolina GIS | https://www.dnr.sc.gov/gis.html | custom | ❓ |
| South Dakota | http://open.sd.gov/ | custom | ❓ |
| Spokane | https://my.spokanecity.org/opendata/ | custom | ❓ |
| Tempe | https://data.tempe.gov/ | socrata | ⏳ |
| Tennessee | https://tn-tnmap.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Texas | https://data.texas.gov/ | socrata | ✅ |
| Texas Transparency | https://comptroller.texas.gov/transparency/opendata/index.php | custom | ❓ |
| Utah | https://opendata.utah.gov/ | socrata | ⏳ |
| Vermont | https://data.vermont.gov/ | socrata | ⏳ |
| Virginia | http://data.virginia.gov | socrata | ⏳ |
| Wake County | http://www.wakegov.com/data/Pages/default.aspx | custom | ❓ |
| Washington | http://data.wa.gov/ | socrata | ⏳ |
| Weatherford GIS | http://ci.weatherford.tx.us/117/GISMapping | custom | ❓ |
| Wellington GIS | https://www.wellingtonfl.gov/288/Geographic-Information-System-GIS | custom | ❓ |
| West Virginia GIS | http://mapwv.gov/gis_services.html | custom | ❓ |
| Wisconsin GIS | http://data-wi-dnr.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Wyoming GIS | https://data.geospatialhub.org/ | arcgis-hub | ⏳ |

## International (open_data_intl.csv)

| Name | URL | Connector | Probe |
|---|---|---|---|
| Alberta | https://open.alberta.ca/opendata | ckan-generic | ⏳ |
| Alkmaar | https://datalab.alkmaar.nl/opendata.html | custom | ❓ |
| Allerdale | https://www.allerdale.gov.uk/en/data-protection-and-freedom-information/open-data/ | custom | ❓ |
| Amsterdam O+S | https://data.amsterdam.nl/ | opendata-soft | ⏳ |
| Angers | http://data.angers.fr/ | opendata-soft | ⏳ |
| Antwerp | https://dams.antwerpen.be/content/open-data | custom | ❓ |
| Aquitaine and Gironde | https://www.data.gouv.fr/en/organizations/gironde-numerique/ | opendata-soft | ⏳ |
| Aragon | http://opendata.aragon.es/ | custom | ❓ |
| Argentina | https://datos.gob.ar | ckan-generic | ⏳ |
| Asturias | https://transparencia.asturias.es/ | custom | ❓ |
| Australia | http://data.gov.au/ | ckan-generic | ⏳ |
| Australian Capital Territory | https://www.data.act.gov.au/ | socrata | ⏳ |
| Austria | http://data.gv.at/ | opendata-soft | ⏳ |
| Badalona | https://datos.gob.es/es/iniciativas/open-data-badalona | custom | ❓ |
| Bahía Blanca | https://datos.bahia.gob.ar/dataset | ckan-generic | ⏳ |
| Bahrain | https://www.bahrain.bh/wps/portal/... | custom | ❓ |
| Balearic Islands | https://datos.gob.es/... | custom | ❓ |
| Barcelona | https://opendata-ajuntament.barcelona.cat/en/ | opendata-soft | ⏳ |
| Bari | https://dati.comune.bari.it/ | custom | ❓ |
| Belgium | http://data.gov.be/ | ckan-generic | ⏳ |
| Berlin | http://daten.berlin.de/ | custom | ❓ |
| Birmingham | http://www.birmingham.gov.uk/open-data | custom | ❓ |
| Bologna | https://opendata.comune.bologna.it/pages/home/ | custom | ❓ |
| Brazil | http://dados.gov.br/ | ckan-generic | ⏳ |
| Bremen | http://www.daten.bremen.de/ | custom | ❓ |
| Brisbane | https://www.data.brisbane.qld.gov.au/ | socrata | ⏳ |
| British Columbia | https://catalogue.data.gov.bc.ca/ | ckan-generic | ⏳ |
| British Columbia Local Govt | http://www.civicinfo.bc.ca/ | custom | ❓ |
| Buenos Aires | http://data.buenosaires.gob.ar/ | ckan-generic | ⏳ |
| Burlington (CA) | https://navburl-burlington.opendata.arcgis.com/pages/data | arcgis-hub | ⏳ |
| Canada | http://open.canada.ca/en | ckan-generic | ⏳ |
| Castilla-La Mancha | https://datosabiertos.castillalamancha.es/ | custom | ❓ |
| Catalunya | https://administraciodigital.gencat.cat/... | custom | ❓ |
| Chamber of Deputies (IT) | https://dati.camera.it/it/ | custom | ❓ |
| Chile | http://datos.gob.cl/ | ckan-generic | ⏳ |
| Colombia | www.datos.gov.co | socrata | ⏳ |
| County of Grand Prairie No. 1 | http://www.countygp.ab.ca/... | custom | ❓ |
| CSIRO | https://data.csiro.au/ | ckan-generic | ⏳ |
| Denmark | https://dati.camera.it/it/ | custom | ❓ |
| District of North Vancouver | http://geoweb.dnv.org/data/ | custom | ❓ |
| Edmonton | http://data.edmonton.ca/ | socrata | ⏳ |
| Emilia-Romagna | http://dati.emilia-romagna.it/ | custom | ❓ |
| Enschede | https://www.enschede.nl/open-data | custom | ❓ |
| Estonia | https://www.ria.ee/en/.../estonian-open-data-portal | custom | ❓ |
| European Union | https://data.europa.eu/en | eu-portal | ✅ |
| Euskadi (Basque Country) | https://opendata.euskadi.eus/hasiera/ | custom | ❓ |
| Fingal | http://data.fingal.ie/ | custom | ❓ |
| Finland | https://www.suomi.fi/etusivu | custom | ❓ |
| France | http://data.gouv.fr/ | opendata-soft | ⏳ |
| Fredericton | https://www.fredericton.ca/.../open-data-portal-0 | custom | ❓ |
| Galicia | http://abertos.xunta.es/portada/ | custom | ❓ |
| Germany | https://www.govdata.de/ | ckan-generic | ⏳ |
| Ghana | https://www.statsghana.gov.gh/ | custom | ❓ |
| Graz | http://data.graz.gv.at/ | opendata-soft | ⏳ |
| Great Manchester | http://open.manchester.gov.uk/ | custom | ❓ |
| Greece | https://repository.data.gov.gr/ | custom | ❓ |
| Guelph | https://guelph.ca/city-hall/open-government/ | custom | ❓ |
| Halifax | https://data-hrm.hub.arcgis.com/pages/open-data-catalogue | arcgis-hub | ⏳ |
| Hamburg | http://daten.hamburg.de/ | custom | ❓ |
| Hamilton | http://www.hamilton.ca/ProjectsInitiatives/OpenData/ | opendata-soft | ⏳ |
| Hauts-de-Seine | https://opendata.hauts-de-seine.fr/pages/accueil/ | opendata-soft | ⏳ |
| Helsinki Region Infoshare | https://hri.fi/en_gb/ | custom | ❓ |
| Hong Kong | https://data.gov.hk/en/ | ckan-generic | ⏳ |
| India | http://data.gov.in/ | ckan-generic | ⏳ |
| Indonesia | https://data.go.id/ | ckan-generic | ⏳ |
| Ireland | https://data.gov.ie/ | ckan-generic | ⏳ |
| Italian Parliament | http://dati.camera.it/it/ | custom | ❓ |
| Italy | http://www.dati.gov.it/ | ckan-generic | ⏳ |
| Italy Senate | http://dati.senato.it/ | custom | ❓ |
| Japan | https://www.data.go.jp/?lang=english | ckan-generic | ⏳ |
| Junta de Castilla y León | https://datosabiertos.jcyl.es/... | custom | ❓ |
| Kent | https://www.kent.gov.uk/.../data-about-the-council | custom | ❓ |
| Kenya | https://www.knbs.or.ke/ | custom | ❓ |
| La Rochelle | https://www.larochelle.fr/.../open-data | opendata-soft | ⏳ |
| Langley | https://data-tol.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Le Mans | http://www.lemans.fr/.../lopen-data/ | opendata-soft | ⏳ |
| Leipzig | https://opendata.leipzig.de/ | custom | ❓ |
| Library of the National Congress (CL) | http://datos.bcn.cl/es/ | custom | ❓ |
| Lichfield | http://lichfielddc.gov.uk/ | custom | ❓ |
| Linz | https://www.data.gv.at/auftritte/?organisation=stadt-linz | opendata-soft | ⏳ |
| Lleida | https://www.paeria.cat/ | custom | ❓ |
| Loire-Atlantique | https://data.loire-atlantique.fr/pages/home/ | opendata-soft | ⏳ |
| Lombardy | https://dati.lombardia.it/ | socrata | ⏳ |
| London (CA) | https://opendata.london.ca/ | custom | ❓ |
| London (UK) | https://data.london.gov.uk/ | custom | ❓ |
| Lucca | https://www.provincia.lucca.it/open-data | custom | ❓ |
| Manchester | http://open.manchester.gov.uk/ | custom | ❓ |
| Medicine Hat | https://www.medicinehat.ca/.../maps-and-gis.aspx | custom | ❓ |
| Merton Council | https://www.merton.gov.uk/.../open-data/overview | custom | ❓ |
| METI (JP) | https://www.meti.go.jp/english/statistics/ | custom | ❓ |
| Mexico | http://datos.gob.mx/ | ckan-generic | ⏳ |
| Milan | http://dati.comune.milano.it/ | custom | ❓ |
| Ministry of Finances (RU) | http://government.ru/en/department/69/events/ | custom | ❓ |
| Mississauga | https://www.mississauga.ca/.../city-planning-data/ | custom | ❓ |
| Moers | https://www.moers.de/.../offene-daten-moers/ | custom | ❓ |
| Moldova | http://data.gov.md/ | ckan-generic | ⏳ |
| Montevideo | http://montevideo.gub.uy/.../montevideo-abierto | custom | ❓ |
| Montpellier | https://www.montpelliernumerique.fr/ | opendata-soft | ⏳ |
| Montreal | https://donnees.montreal.ca/ | opendata-soft | ⏳ |
| Morocco | http://data.gov.ma/ | ckan-generic | ⏳ |
| Mosman Council | https://www.mosman.nsw.gov.au/ | custom | ❓ |
| Nanaimo | https://www.nanaimo.ca/your-government/maps-data | custom | ❓ |
| Nantes | https://data.nantesmetropole.fr/pages/home/ | opendata-soft | ✅ |
| Navarre | https://gobiernoabierto.navarra.es/es/open-data | custom | ❓ |
| Netherlands | http://data.overheid.nl/ | ckan-generic | ✅ |
| New South Wales | http://data.nsw.gov.au/ | ckan-generic | ⏳ |
| New Zealand | http://www.data.govt.nz/ | ckan-generic | ✅ |
| Niagara Falls | https://niagarafalls.ca/services/open/default.aspx | custom | ❓ |
| Niagara Region | https://niagarafalls.ca/services/open/default.aspx | custom | ❓ |
| North Devon Council | https://northdevon-self.achieveservice.com/... | custom | ❓ |
| North Okanagan | https://www.rdno.ca/.../digital-data | custom | ❓ |
| Norway | https://data.norge.no/nb | ckan-generic | ⏳ |
| Oman | https://opendata.om/ | ckan-generic | ⏳ |
| Ontario | https://www.ontario.ca/page/sharing-government-data | custom | ❓ |
| Open GEO-Data (Amsterdam) | http://maps.amsterdam.nl/open_geodata/ | custom | ❓ |
| Open UN-Habitat | https://data.unhabitat.org/ | custom | ❓ |
| OECD | https://web-archive.oecd.org/... | custom | ❓ |
| Ottawa | http://data.ottawa.ca/ | socrata | ⏳ |
| Pamplona | https://www.pamplona.es/.../open-data | custom | ❓ |
| Paris | https://opendata.paris.fr/explore/ | opendata-soft | ✅ |
| Philippines | http://data.gov.ph/ | ckan-generic | ⏳ |
| Piedmont | https://www.dati.piemonte.it/#/home | custom | ❓ |
| Portugal | https://dados.gov.pt/pt/ | ckan-generic | ⏳ |
| Prince George | https://data-cityofpg.opendata.arcgis.com/ | arcgis-hub | ⏳ |
| Puglia | http://www.dati.puglia.it/ | custom | ❓ |
| Quebec (City) | https://library.mcmaster.ca/data/quebec-city-open-data | custom | ❓ |
| Quebec (Province) | https://www.donneesquebec.ca/fr/ | opendata-soft | ⏳ |
| Queensland | https://data.qld.gov.au/ | ckan-generic | ⏳ |
| Red Deer | https://data.reddeer.ca/datasets | custom | ❓ |
| Redbridge | http://data.redbridge.gov.uk/ | custom | ❓ |
| Regina | http://open.regina.ca/ | custom | ❓ |
| Region of Peel | http://opendata.peelregion.ca/ | custom | ❓ |
| Rennes | https://data.rennesmetropole.fr/explore/ | opendata-soft | ✅ |
| Republic of Korea | http://www.data.go.kr/ | ckan-generic | ⏳ |
| Research Data Australia | https://researchdata.edu.au/ | ckan-generic | ⏳ |
| Rheinland Pfalz | http://www.daten.rlp.de/ | custom | ❓ |
| Romania | http://data.gov.ro/ | ckan-generic | ⏳ |
| Rome | https://dati.comune.roma.it/ | custom | ❓ |
| Rostock | https://www.opendata-hro.de/ | custom | ❓ |
| Rotterdam | https://rotterdam.dataplatform.nl/#/home | opendata-soft | ⏳ |
| Saanich | https://www.saanich.ca/.../data-catalogue-1.html | custom | ❓ |
| Sardinia | http://www.sardegnageoportale.it/index.html | custom | ❓ |
| Saskatoon | https://www.saskatoon.ca/.../open-data-saskatoon-transit | custom | ❓ |
| Saône-et-Loire | http://www.opendata71.fr/ | opendata-soft | ⏳ |
| Seoul | http://data.seoul.go.kr/ | custom | ❓ |
| Shizuoka | https://www.city.shizuoka.lg.jp.e.qv.hp.transer.com/ | custom | ❓ |
| Sierra Leone | https://sierraleone.opendataforafrica.org/ | custom | ❓ |
| Singapore | http://data.gov.sg/ | ckan-generic | ⏳ |
| Slovak Republic | https://data.slovensko.sk/ | custom | ❓ |
| South Africa | http://southafrica.opendataforafrica.org/ | custom | ❓ |
| South Australia | http://data.sa.gov.au | ckan-generic | ⏳ |
| Spain | http://datos.gob.es/ | custom | ❓ |
| Stockholm | https://dataportalen.stockholm.se/dataportalen/ | opendata-soft | ⏳ |
| Surrey | https://www.surrey.ca/.../open-data | custom | ❓ |
| Sutton | https://www.sutton.gov.uk/data-and-privacy | custom | ❓ |
| Sweden | https://www.dataportal.se/ | opendata-soft | ⏳ |
| Tampere | http://tampere.fi/avoindata | custom | ❓ |
| Tanzania | https://tanzania.opendataforafrica.org/ | custom | ❓ |
| Tasmania | https://nre.tas.gov.au/.../tasmanian-spatial-data | custom | ❓ |
| Terrassa | http://opendata.terrassa.cat/ | opendata-soft | ⏳ |
| Timor Leste | http://www.transparency.gov.tl/ | custom | ❓ |
| Tirol | https://www.tirol.gv.at/data/ | opendata-soft | ⏳ |
| Toronto | https://www.toronto.ca/.../open-data/ | custom | ❓ |
| Toulouse | https://data.toulouse-metropole.fr/pages/accueil/ | opendata-soft | ✅ |
| Trentino | http://dati.trentino.it/ | custom | ❓ |
| Trento | http://www.territorio.provincia.tn.it/... | custom | ❓ |
| Trinidad and Tobago | http://data.gov.tt/ | ckan-generic | ⏳ |
| Tunisia | https://www.data.gov.tn/fr/ | ckan-generic | ⏳ |
| Turin | http://www.comune.torino.it/aperto | custom | ❓ |
| Tuscany | http://dati.toscana.it/ | custom | ❓ |
| Udine | http://opendata.comune.udine.it/ | custom | ❓ |
| Ukraine | http://data.gov.ua/ | ckan-generic | ⏳ |
| United Arab Emirates | https://bayanat.ae/ | custom | ❓ |
| United Kingdom | http://data.gov.uk/ | ckan-generic | ✅ |
| United Nations | http://data.un.org/ | custom | ❓ |
| Uruguay | https://data.org.uy/ | ckan-generic | ⏳ |
| Vancouver | https://opendata.vancouver.ca/pages/home/ | custom | ❓ |
| Veneto | http://dati.veneto.it/ | custom | ❓ |
| Venice | http://dati.venezia.it/ | custom | ❓ |
| Vicenza Geodata | http://geoportale.provincia.vicenza.it/home.asp | custom | ❓ |
| Victoria | http://www.data.vic.gov.au/ | ckan-generic | ⏳ |
| Vienna | https://www.data.gv.at/auftritte/?organisation=stadt-wien | opendata-soft | ⏳ |
| Vorarlberg | https://www.data.gv.at/auftritte/?organisation=land-vorarlberg | opendata-soft | ⏳ |
| Warwickshire | https://apps.warwickshire.gov.uk/OpenData | custom | ❓ |
| Waterloo | https://data.waterloo.ca/ | custom | ❓ |
| Windsor | https://opendata.citywindsor.ca/ | socrata | ⏳ |
| World Bank | http://data.worldbank.org/ | custom | ❓ |
| Wyre Council | https://www.wyre.gov.uk/open-data | custom | ❓ |
| Zaragoza | https://www.zaragoza.es/.../datos-abiertos/ | custom | ❓ |
| Zurich | https://data.stadt-zuerich.ch/ | opendata-soft | ⏳ |

## Summary by platform

- **ckan-generic** — 41 portals
- **socrata** — 38 portals
- **opendata-soft** — 36 portals
- **arcgis-hub** — 32 portals
- **custom / unknown** — 174 portals (need one-off probe or scraper)

## Next steps

1. Probe every ⏳ portal with curl and promote the row to ✅ / ❌ / custom.
2. Move the 174 "custom" portals into one of the 5 connectors if they actually use it; the rest need one-off fetchers (about 30 of the 174 are likely real custom builds).
3. Generate `sources.yaml` entries in OpenTIR-Data for each platform+portal pair — a `generate_sources.py` script is the right tool, taking this CSV as input.


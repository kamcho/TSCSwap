from django.core.management.base import BaseCommand
from home.models import Counties, Constituencies, Wards

class Command(BaseCommand):
    help = 'Populates the database with Kenya administrative data (Counties, Constituencies, Wards)'

    def handle(self, *args, **options):
        # Kenya administrative data
        KENYA_ADMIN = {

            "Baringo": {
                "Baringo North": [
                    "Barwessa",
                    "Kabartonjo",
                    "Saimo/Kipsaraman",
                    "Saimo/Soi",
                    "Bartabwa",
                ],
                "Baringo Central": [
                    "Kabarnet",
                    "Sacho",
                    "Tenges",
                    "Ewalel/Chapchap",
                    "Kapropita",
                ],
                "Baringo South": [
                    "Mochongoi",
                    "Mukutani",
                    "Marigat",
                    "Ilchamus",
                ],
                "Eldama Ravine": [
                    "Lembus",
                    "Lembus Kwen",
                    "Ravine",
                    "Mumberes/Maji Mazuri",
                    "Lembus/Perkerra",
                ],
                "Tiaty": [
                    "Tirioko",
                    "Kolowa",
                    "Ribkwo",
                    "Silale",
                    "Loiyamorock",
                    "Tangulbei/Korossi",
                    "Churo/Amaya",
                ],
            },

            "Bomet": {
                "Bomet Central": [
                    "Silibwet Township",
                    "Ndaraweta",
                    "Singorwet",
                    "Chesoen",
                    "Mutarakwa",
                ],
                "Bomet East": [
                    "Merigi",
                    "Kembu",
                    "Longisa",
                    "Kipreres",
                    "Chemaner",
                ],
                "Chepalungu": [
                    "Chepalungu",
                    "Sigor",
                    "Chebunyo",
                    "Siongiroi",
                ],
                "Sotik": [
                    "Ndanai/Abosi",
                    "Chemagel",
                    "Kapletundo",
                    "Rongena/Manaret",
                ],
                "Konoin": [
                    "Kimulot",
                    "Mogogosiek",
                    "Boito",
                    "Embomos",
                ],
            },

            "Bungoma": {
                "Bumula": [
                    "Bumula",
                    "Kabula",
                    "Kimaeti",
                    "South Bukusu",
                    "Siboti",
                ],
                "Kabuchai": [
                    "Kabuchai/Chwele",
                    "West Nalondo",
                    "Bwake/Luuya",
                    "Mukuyuni",
                ],
                "Kanduyi": [
                    "Bukembe West",
                    "Bukembe East",
                    "Township",
                    "Khalaba",
                    "Musikoma",
                    "East Sang'alo",
                    "West Sang'alo",
                ],
                "Kimilili": [
                    "Kimilili",
                    "Maeni",
                    "Kamukuywa",
                ],
                "Mt. Elgon": [
                    "Cheptais",
                    "Chesikaki",
                    "Chepyuk",
                    "Kapkateny",
                    "Kaptama",
                    "Elgon",
                ],
                "Sirisia": [
                    "Namwela",
                    "Malakisi/South Kulisiru",
                    "Lwandanyi",
                ],
                "Tongaren": [
                    "Mihuu",
                    "Naitiri/Kabuyefwe",
                    "Milima",
                    "Ndalu/Tabani",
                    "Tongaren",
                    "Soysambu/Mitua",
                ],
                "Webuye East": [
                    "Webuye East",
                    "Mihuu",
                ],
                "Webuye West": [
                    "Webuye West",
                    "Misikhu",
                    "Matulo",
                ],
            },

            "Busia": {
                "Budalangi": [
                    "Bunyala Central",
                    "Bunyala North",
                    "Bunyala South",
                    "Bunyala West",
                ],
                "Butula": [
                    "Marachi West",
                    "Marachi Central",
                    "Marachi East",
                    "Marachi North",
                    "Elugulu",
                ],
                "Funyula": [
                    "Namboboto/Nambuku",
                    "Ageng'a Nanguba",
                    "Bwiri",
                ],
                "Matayos": [
                    "Bukhayo West",
                    "Bukhayo East",
                    "Bukhayo Central",
                ],
                "Nambale": [
                    "Nambale Township",
                    "Bukhayo North/Walatsi",
                    "Bukhayo South/Buyofu",
                ],
                "Teso North": [
                    "Malaba Central",
                    "Malaba North",
                    "Ang'urai South",
                    "Ang'urai North",
                    "Ang'urai East",
                ],
                "Teso South": [
                    "Amukura West",
                    "Amukura East",
                    "Amukura Central",
                ],
            },

            "Elgeyo-Marakwet": {
                "Keiyo North": [
                    "Emsoo",
                    "Kamariny",
                    "Kapchemutwa",
                    "Tambach",
                ],
                "Keiyo South": [
                    "Kaptarakwa",
                    "Chepkorio",
                    "Soy North",
                    "Soy South",
                    "Kabiemit",
                    "Metkei",
                ],
                "Marakwet East": [
                    "Kapyego",
                    "Sambirir",
                    "Endo",
                    "Embobut/Embulot",
                ],
                "Marakwet West": [
                    "Lelan",
                    "Sengwer",
                    "Cherang'any/Chebororwa",
                    "Moiben/Kuserwo",
                ],
            },

        }

        KENYA_ADMIN.update({

            "West Pokot": {
                "Kapenguria": ["Kapenguria Central", "Kapenguria East", "Kapenguria West"],
                "Sigor": ["Sigor Central", "Sigor East", "Sigor West"],
                "Kacheliba": ["Kacheliba Central", "Kacheliba East", "Kacheliba West"],
                "Pokot South": ["Pokot South Central", "Pokot South East", "Pokot South West"],
                "Sambirir": ["Sambirir Central", "Sambirir East", "Sambirir West"],
            },

            "Nyamira": {
                "Nyamira North": ["Bogetenga", "Nyamira Central", "Nyamira East"],
                "Nyamira South": ["Ekerenyo", "Bosamaro", "Nyamira West"],
                "Borabu": ["Masaba North", "Masaba South", "Borabu Central"],
                "Manga": ["Manga East", "Manga Central", "Manga West"],
                "Masaba": ["Masaba East", "Masaba West", "Masaba Central"],
            },

        })
        KENYA_ADMIN.update({

            "Trans Nzoia": {
                "Kiminini": ["Kiminini Central", "Kiminini East", "Kiminini West"],
                "Cherangany": ["Cherangany Central", "Cherangany East", "Cherangany West"],
                "Saboti": ["Saboti Central", "Saboti East", "Saboti West"],
                "Kwanza": ["Kwanza Central", "Kwanza East", "Kwanza West"],
                "Endebess": ["Endebess Central", "Endebess North", "Endebess South"],
            },

            "Turkana": {
                "Turkana North": ["Lobei", "Lokichar", "Kanyaluo"],
                "Turkana Central": ["Lodwar", "Nakapiripirit", "Turkwel"],
                "Turkana East": ["Kachoda", "Kapedo", "Loima"],
                "Turkana South": ["Lokichoggio", "Nakalale", "Katilu"],
                "Turkana West": ["Lopiding", "Kakuma", "Kapedo West"],
            },

            "Uasin Gishu": {
                "Eldoret North": ["Kapseret", "Kapsabet North", "Moiben"],
                "Eldoret South": ["Soy", "Turbo", "Ainabkoi"],
                "Kesses": ["Kesses Central", "Kesses East", "Kesses West"],
                "Moiben": ["Moiben Central", "Moiben East", "Moiben West"],
            },

            "Vihiga": {
                "Vihiga": ["Vihiga Central", "Vihiga East", "Vihiga West"],
                "Emuhaya": ["Emuhaya Central", "Emuhaya East", "Emuhaya West"],
                "Sabatia": ["Sabatia Central", "Sabatia East", "Sabatia West"],
                "Hamisi": ["Hamisi Central", "Hamisi East", "Hamisi West"],
                "Luanda": ["Luanda Central", "Luanda East", "Luanda West"],
            },

            "Wajir": {
                "Wajir East": ["Bute", "Eliye Springs", "Bassa"],
                "Wajir West": ["Tarbaj", "Burat", "Eliye"],
                "Wajir North": ["Mogogosiek", "Griftu", "Habaswein"],
                "Wajir South": ["Buna", "Korondille", "Guris"],
                "Wajir Central": ["Wajir Town", "Arabia", "Malkamari"],
            },

        })
        KENYA_ADMIN.update({

            "Samburu": {
                "Samburu East": ["Wamba", "Beleso", "Samburu East Central"],
                "Samburu North": ["Suguta Marmar", "Maralal", "Lorroki"],
                "Samburu West": ["Poro", "Nyiro", "Wamba West"],
            },

            "Siaya": {
                "Siaya": ["Siaya Central", "Siaya East", "Siaya West", "Ugunja"],
                "Bondo": ["Bondo Central", "Bondo East", "Rarieda", "Bondo West"],
                "Rarieda": ["Rarieda North", "Rarieda Central", "Rarieda South"],
                "Ugenya": ["Ugenya Central", "Ugenya East", "Ugenya West"],
                "Alego Usonga": ["Alego Central", "Usonga East", "Alego West"],
            },

            "Taita Taveta": {
                "Mwatate": ["Mwatate Town", "Mwachabo", "Wundanyi"],
                "Voi": ["Voi Town", "Kasigau", "Chawia"],
                "Taveta": ["Taveta Town", "Kilema", "Chala"],
                "Wundanyi": ["Wundanyi Town", "Mwatate", "Mghange"],
                "Mbololo": ["Mbololo Central", "Mbololo East", "Mbololo West"],
            },

            "Tana River": {
                "Bura": ["Bura Central", "Bura North", "Bura South"],
                "Garsen": ["Garsen Central", "Garsen North", "Garsen South"],
                "Galole": ["Galole Central", "Galole North", "Galole South"],
            },

            "Tharaka Nithi": {
                "Tharaka": ["Tharaka Central", "Tharaka South", "Tharaka North"],
                "Meru South": ["Chuka Town", "Meru South Central", "Meru South West"],
                "Chuka/Igambang’ombe": ["Chuka Central", "Igambang’ombe East", "Igambang’ombe West"],
                "Maara": ["Maara Central", "Maara North", "Maara South"],
            },

        })
        KENYA_ADMIN.update({

            "Nandi": {
                "Aldai": ["Chesumei", "Chemase", "Kapkangani", "Ndalat"],
                "Chesumei": ["Kipkoi/Kapsaos", "Chemundu", "Chesumei"],
                "Emgwen": ["Kipkoi", "Kipkenyo", "Kipchorian", "Kapsabet", "Kapsaos"],
                "Mosop": ["Kapsabet East", "Kapsabet West", "Kaptumo", "Nandi Hills"],
                "Tinderet": ["Keben", "Lelmokwo", "Nandi Hills", "Tinderet"],
                "Kosirai": ["Kabiyet", "Kapsuser", "Kosirai"],
                "Nandi Hills": ["Nandi Hills Central", "Nandi Hills East", "Nandi Hills West"],
            },

            "Narok": {
                "Emurua Dikirr": ["Mosiro", "Emurua", "Ilkerin"],
                "Kilgoris": ["Kinyala", "Siana", "Kilgoris", "Magadi"],
                "Loita": ["Ololulunga", "Loita", "Entasekera"],
                "Narok East": ["Olpusimoru", "Narok North", "Narok South", "Narok East"],
                "Narok North": ["Olokurto", "Naikarra", "Narok North Central"],
                "Narok South": ["Emurua Dikirr", "Kilgoris South", "Narok South East"],
                "Narok West": ["Oloisukut", "Lemek", "Loita West"],
                "Transmara East": ["Kilgoris East", "Isinya", "Transmara East"],
                "Transmara West": ["Kilgoris West", "Isbii", "Transmara West"],
            },

            "Nyamira": {
                "Borabu": ["Nyansiongo", "Masaba", "Ekerenyo"],
                "Nyamira": ["Nyamira Town", "Bogichora", "Bonyakoni", "Nyamira North"],
                "West Mugirango": ["Etago", "Sironga", "Gorora", "Banyamogoto"],
                "North Mugirango": ["Rigoma", "Bomorenda", "Bokimonge"],
                "Masaba": ["Masaba Central", "Masaba North", "Masaba East"],
            },

            "Nyandarua": {
                "Kinangop": ["Kaimbaga", "Gatimu", "Wanjohi", "Njabini"],
                "Kipipiri": ["Mitunguu", "Kipipiri", "Wanjohi"],
                "Ndaragwa": ["Kaburu", "Mutarakwa", "Gathara"],
                "Ol Kalou": ["Ol Kalou Town", "Rurii", "Kaimbaga"],
                "Nyandarua West": ["Weru", "Mutarakwa", "Kaimbaga"],
            },

            "Nyeri": {
                "Tetu": ["Tetu Central", "Kagumo", "Muruguru", "Karimaini"],
                "Mathira": ["Karatina Town", "Mathira East", "Mathira West"],
                "Kieni": ["Ndia", "Kieni East", "Kieni West"],
                "Othaya": ["Othaya Town", "Chinga", "Mahiga"],
                "Nyeri Town": ["Nyeri Town East", "Nyeri Town West", "Ruringu"],
                "Mukurweini": ["Gathugu", "Kaharo", "Mukurweini"],
            },

        })
        KENYA_ADMIN.update({

            "Meru": {
                "Buuri": [
                    "Timau",
                    "Kisima",
                    "Kiirua/Naari",
                    "Ruiri/Rwarera",
                ],
                "Central Imenti": [
                    "Mwanganthia",
                    "Abothuguchi Central",
                    "Abothuguchi West",
                    "Kiagu",
                ],
                "Igembe Central": [
                    "Akirang'ondu",
                    "Athiru Ruujine",
                    "Igembe East",
                    "Njia",
                ],
                "Igembe North": [
                    "Antuambui",
                    "Ntunene",
                    "Antubetwe Kiongo",
                    "Naathu",
                    "Amwathi",
                ],
                "Igembe South": [
                    "Maua",
                    "Kiegoi/Antubochiu",
                    "Athiru Gaiti",
                    "Kanuni",
                ],
                "North Imenti": [
                    "Municipality",
                    "Ntima East",
                    "Ntima West",
                    "Nyaki West",
                    "Nyaki East",
                ],
                "South Imenti": [
                    "Mitunguu",
                    "Igoji East",
                    "Igoji West",
                    "Abogeta East",
                    "Abogeta West",
                ],
                "Tigania East": [
                    "Thangatha",
                    "Mikinduri",
                    "Kianjai",
                    "Nkomo",
                ],
                "Tigania West": [
                    "Athwana",
                    "Akithii",
                    "Kianjai",
                    "Mbeu",
                ],
            },

            "Migori": {
                "Awendo": [
                    "North Sakwa",
                    "South Sakwa",
                    "West Sakwa",
                    "Central Sakwa",
                ],
                "Kuria East": [
                    "Bugumbe",
                    "Nyamosense/Komosoko",
                    "Ntimaru East",
                    "Ntimaru West",
                ],
                "Kuria West": [
                    "Bukira East",
                    "Bukira Central",
                    "Bukira South",
                    "Isibania",
                    "Makerero",
                    "Masaba",
                    "Tagare",
                ],
                "Nyatike": [
                    "Kachieng",
                    "Kanyasa",
                    "North Kadem",
                    "Macalder/Kanyarwanda",
                    "Got Kachola",
                    "Muhuru",
                ],
                "Rongo": [
                    "North Kamagambo",
                    "Central Kamagambo",
                    "East Kamagambo",
                ],
                "Suna East": [
                    "God Jope",
                    "Suna Central",
                    "Kakrao",
                ],
                "Suna West": [
                    "Wasweta II",
                    "Wasimbete",
                    "West Wasweta",
                    "Central Wasweta",
                ],
                "Uriri": [
                    "Central Kanyamkago",
                    "North Kanyamkago",
                    "South Kanyamkago",
                    "West Kanyamkago",
                ],
            },

            "Murang’a": {
                "Gatanga": [
                    "Kariara",
                    "Gatanga",
                    "Kakuzi/Mitubiri",
                    "Mugumo-ini",
                    "Kihumbu-ini",
                    "Gatanga",
                ],
                "Kahuro": [
                    "Mugoiri",
                    "Mbiri",
                    "Kahuro",
                ],
                "Kandara": [
                    "Gaichanjiru",
                    "Ithiru",
                    "Ruchu",
                    "Muruka",
                ],
                "Kangema": [
                    "Kangema",
                    "Kanyenyaini",
                    "Muguru",
                ],
                "Kigumo": [
                    "Kigumo",
                    "Kinyona",
                    "Muthithi",
                    "Kahumbu",
                    "Gaturi",
                ],
                "Kiharu": [
                    "Mugoiri",
                    "Township",
                    "Gaturi",
                    "Kimorori/Wempa",
                ],
                "Mathioya": [
                    "Kirimukuyu",
                    "Kamacharia",
                    "Gitugi",
                ],
            },

            "Nairobi": {
                "Dagoretti North": [
                    "Kilimani",
                    "Kawangware",
                    "Gatina",
                    "Kileleshwa",
                    "Kabiro",
                ],
                "Dagoretti South": [
                    "Mutu-ini",
                    "Ngando",
                    "Riruta",
                    "Uthiru/Ruthimitu",
                    "Waithaka",
                ],
                "Embakasi Central": [
                    "Kayole North",
                    "Kayole Central",
                    "Kayole South",
                    "Komarock",
                    "Matopeni/Spring Valley",
                ],
                "Embakasi East": [
                    "Upper Savannah",
                    "Lower Savannah",
                    "Embakasi",
                    "Utawala",
                    "Mihango",
                ],
                "Embakasi North": [
                    "Kariobangi North",
                    "Dandora Area I",
                    "Dandora Area II",
                    "Dandora Area III",
                    "Dandora Area IV",
                ],
                "Embakasi South": [
                    "Imara Daima",
                    "Kwa Njenga",
                    "Kwa Reuben",
                    "Pipeline",
                    "Kware",
                ],
                "Embakasi West": [
                    "Umoja I",
                    "Umoja II",
                    "Mowlem",
                    "Kariobangi South",
                ],
                "Kamukunji": [
                    "Pumwani",
                    "Eastleigh North",
                    "Eastleigh South",
                    "Airbase",
                    "California",
                ],
                "Kasarani": [
                    "Clay City",
                    "Mwiki",
                    "Kasarani",
                    "Njiru",
                    "Ruai",
                ],
                "Kibra": [
                    "Laini Saba",
                    "Lindi",
                    "Makina",
                    "Woodley/Kenyatta Golf Course",
                    "Sarangombe",
                ],
                "Lang’ata": [
                    "Karen",
                    "Nairobi West",
                    "Mugumo-ini",
                    "South C",
                    "Nyayo Highrise",
                ],
                "Makadara": [
                    "Maringo/Hamza",
                    "Viwandani",
                    "Harambee",
                    "Makongeni",
                ],
                "Mathare": [
                    "Hospital",
                    "Mabatini",
                    "Huruma",
                    "Ngei",
                    "Mlango Kubwa",
                    "Kiamaiko",
                ],
                "Roysambu": [
                    "Githurai",
                    "Kahawa West",
                    "Zimmerman",
                    "Roysambu",
                    "Kahawa",
                ],
                "Starehe": [
                    "Nairobi Central",
                    "Ngara",
                    "Pangani",
                    "Ziwani/Kariokor",
                    "Landimawe",
                    "Nairobi South",
                ],
                "Westlands": [
                    "Kitisuru",
                    "Parklands/Highridge",
                    "Karura",
                    "Kangemi",
                    "Mountain View",
                ],
            },

            "Nakuru": {
                "Bahati": [
                    "Bahati",
                    "Kabatini",
                    "Dundori",
                    "Kiamaina",
                    "Lanet/Umoja",
                ],
                "Gilgil": [
                    "Gilgil",
                    "Elementaita",
                    "Mbaruk/Eburu",
                    "Malewa West",
                    "Murindat",
                ],
                "Kuresoi North": [
                    "Kiptororo",
                    "Nyota",
                    "Sirikwa",
                    "Kamara",
                ],
                "Kuresoi South": [
                    "Amalo",
                    "Keringet",
                    "Tinet",
                    "Kiptagich",
                ],
                "Molo": [
                    "Mariashoni",
                    "Elburgon",
                    "Turi",
                    "Molo",
                ],
                "Naivasha": [
                    "Biashara",
                    "Hells Gate",
                    "Lakeview",
                    "Maai Mahiu",
                    "Olkaria",
                    "Naivasha East",
                    "Viwandani",
                ],
                "Nakuru Town East": [
                    "Biashara",
                    "Kivumbini",
                    "Flamingo",
                    "Menengai",
                    "Nakuru East",
                ],
                "Nakuru Town West": [
                    "Barut",
                    "London",
                    "Kaptembwa",
                    "Rhoda",
                    "Shaabab",
                ],
                "Njoro": [
                    "Mauche",
                    "Kihingo",
                    "Nessuit",
                    "Lare",
                    "Njoro",
                ],
                "Rongai": [
                    "Menengai West",
                    "Soin",
                    "Mosop",
                    "Solai",
                    "Visoi",
                ],
                "Subukia": [
                    "Subukia",
                    "Waseges",
                    "Kabazi",
                ],
            },

        })
        KENYA_ADMIN.update({

            "Lamu": {
                "Lamu East": [
                    "Faza",
                    "Kiunga",
                    "Basuba",
                ],
                "Lamu West": [
                    "Shella",
                    "Mkomani",
                    "Hindi",
                    "Mkunumbi",
                    "Hongwe",
                    "Witu",
                    "Bahari",
                ],
            },

            "Machakos": {
                "Kathiani": [
                    "Mitaboni",
                    "Kathiani Central",
                    "Upper Kaewa/Iveti",
                    "Lower Kaewa/Kaani",
                ],
                "Machakos Town": [
                    "Mua",
                    "Mutituni",
                    "Machakos Central",
                    "Mumbuni North",
                    "Mumbuni South",
                ],
                "Masinga": [
                    "Kivaa",
                    "Masinga Central",
                    "Ekalakala",
                    "Muthesya",
                ],
                "Matungulu": [
                    "Tala",
                    "Matungulu North",
                    "Matungulu East",
                    "Matungulu West",
                    "Kyeleni",
                ],
                "Mavoko": [
                    "Athi River",
                    "Kinanie",
                    "Mlolongo",
                    "Syokimau/Mulolongo",
                ],
                "Mwala": [
                    "Muthetheni",
                    "Mwala",
                    "Masii",
                    "Kibauni",
                    "Makutano/Mwala",
                ],
                "Yatta": [
                    "Ndalani",
                    "Matuu",
                    "Kithimani",
                    "Ikombe",
                    "Katangi",
                ],
            },

            "Makueni": {
                "Kaiti": [
                    "Ukia",
                    "Kee",
                    "Kilungu",
                    "Ilima",
                ],
                "Kibwezi East": [
                    "Masongaleni",
                    "Mtito Andei",
                    "Thange",
                    "Ivingoni/Nzambani",
                ],
                "Kibwezi West": [
                    "Makindu",
                    "Nguu/Masumba",
                    "Kikumbulyu North",
                    "Kikumbulyu South",
                    "Nguumo",
                ],
                "Kilome": [
                    "Kasikeu",
                    "Mukaa",
                ],
                "Makueni": [
                    "Wote",
                    "Muvau/Kikuumini",
                    "Mavindini",
                    "Kitise/Kithuki",
                    "Kathonzweni",
                    "Nzaui/Kilili/Kalamba",
                ],
                "Mbooni": [
                    "Tulimani",
                    "Mbooni",
                    "Kithungo/Kitundu",
                    "Kisau/Kiteta",
                    "Waia/Kako",
                ],
            },

            "Mandera": {
                "Banissa": [
                    "Banissa",
                    "Derkhale",
                    "Guba",
                    "Malkamari",
                    "Kiliwehiri",
                ],
                "Lafey": [
                    "Lafey",
                    "Sala",
                    "Warankara",
                    "Alango Gof",
                ],
                "Mandera East": [
                    "Neboi",
                    "Township",
                    "Khalalio",
                ],
                "Mandera North": [
                    "Rhamu Dimtu",
                    "Rhamu",
                    "Ashabito",
                    "Guticha",
                ],
                "Mandera South": [
                    "Elwak South",
                    "Elwak North",
                    "Shimbir Fatuma",
                    "Wargadud",
                ],
                "Mandera West": [
                    "Takaba South",
                    "Takaba",
                    "Dandu",
                    "Gither",
                ],
            },

            "Marsabit": {
                "Laisamis": [
                    "Laisamis",
                    "Logologo",
                    "Kargi/South Horr",
                    "Korr/Ngurunit",
                ],
                "Moyale": [
                    "Butiye",
                    "Sololo",
                    "Heillu/Manyatta",
                    "Golbo",
                    "Moyale Township",
                    "Uran",
                ],
                "North Horr": [
                    "North Horr",
                    "Dukana",
                    "Maikona",
                    "Turbi",
                ],
                "Saku": [
                    "Marsabit Central",
                    "Sagante/Jaldesa",
                    "Karare",
                ],
            },

        })

        KENYA_ADMIN.update({

            "Kisii": {
                "Bobasi": [
                    "Masige West",
                    "Masige East",
                    "Bobasi Central",
                    "Nyacheki",
                    "Bobasi Chache",
                ],
                "Bomachoge Borabu": [
                    "Boochi Borabu",
                    "Bokimonge",
                    "Magenche",
                ],
                "Bomachoge Chache": [
                    "Boochi/Tendere",
                    "Bosoti/Sengera",
                    "Ichuni",
                    "Nyatieko",
                ],
                "Bonchari": [
                    "Riana",
                    "Bomariba",
                    "Bogiakumu",
                    "Bomorenda",
                ],
                "Kitutu Chache North": [
                    "Monyerero",
                    "Sensi",
                    "Marani",
                    "Kisii Central",
                ],
                "Kitutu Chache South": [
                    "Bogusero",
                    "Bogeka",
                    "Nyakoe",
                    "Kitutu Central",
                ],
                "Nyaribari Chache": [
                    "Bobaracho",
                    "Kisii Town",
                    "Keumbu",
                    "Kiogoro",
                ],
                "Nyaribari Masaba": [
                    "Ichuni",
                    "Masimba",
                    "Gesusu",
                    "Kiamokama",
                ],
                "South Mugirango": [
                    "Tabaka",
                    "Boikang'a",
                    "Moticho",
                    "Getenga",
                ],
            },

            "Kisumu": {
                "Kisumu Central": [
                    "Railways",
                    "Shaurimoyo Kaloleni",
                    "Market Milimani",
                    "Kondele",
                    "Nyalenda A",
                    "Nyalenda B",
                ],
                "Kisumu East": [
                    "Kajulu",
                    "Kolwa East",
                    "Manyatta B",
                    "Nyalenda A",
                ],
                "Kisumu West": [
                    "South West Kisumu",
                    "Central Kisumu",
                    "North West Kisumu",
                    "West Kisumu",
                ],
                "Muhoroni": [
                    "Miwani",
                    "Ombeyi",
                    "Masogo/Nyang'oma",
                    "Chemelil",
                    "Muhoroni/Koru",
                ],
                "Nyakach": [
                    "West Nyakach",
                    "North Nyakach",
                    "Central Nyakach",
                    "South Nyakach",
                    "East Nyakach",
                ],
                "Nyando": [
                    "East Kano/Wawidhi",
                    "Awasi/Onjiko",
                    "Ahero",
                    "Kabonyo/Kanyagwal",
                    "Kobura",
                ],
                "Seme": [
                    "West Seme",
                    "Central Seme",
                    "East Seme",
                    "North Seme",
                ],
            },

            "Kitui": {
                "Kitui Central": [
                    "Miambani",
                    "Township",
                    "Kyangwithya West",
                    "Mulango",
                    "Kyangwithya East",
                ],
                "Kitui East": [
                    "Zombe/Mwitika",
                    "Nzambani",
                    "Chuluni",
                    "Endau/Malalani",
                    "Mutito/Kaliku",
                ],
                "Kitui Rural": [
                    "Kisasi",
                    "Mbitini",
                    "Kwavonza/Yatta",
                    "Kanyangi",
                ],
                "Kitui South": [
                    "Ikanga/Kyatune",
                    "Mutomo",
                    "Mutha",
                    "Ikutha",
                    "Kanziko",
                    "Athi",
                ],
                "Kitui West": [
                    "Matinyani",
                    "Kauwi",
                    "Mutonguni",
                    "Kyangwithya West",
                ],
                "Mwingi Central": [
                    "Central",
                    "Kivou",
                    "Nguni",
                    "Nuu",
                    "Mui",
                    "Waita",
                ],
                "Mwingi North": [
                    "Kyuso",
                    "Ngomeni",
                    "Tseikuru",
                    "Tharaka",
                ],
                "Mwingi West": [
                    "Mutitu",
                    "Kaliku",
                    "Mwingi West",
                    "Kyangwithya",
                ],
            },

            "Kwale": {
                "Kinango": [
                    "Ndavaya",
                    "Puma",
                    "Kinango",
                    "Mackinnon Road",
                    "Chengoni/Samburu",
                ],
                "Lunga Lunga": [
                    "Pongwe/Kikoneni",
                    "Dzombo",
                    "Mwereni",
                    "Vanga",
                ],
                "Matuga": [
                    "Tsimba Golini",
                    "Waa",
                    "Tiwi",
                    "Kubo South",
                    "Mkongani",
                ],
                "Msambweni": [
                    "Gombato Bongwe",
                    "Ukunda",
                    "Kinondo",
                    "Ramisi",
                ],
            },

            "Laikipia": {
                "Laikipia East": [
                    "Ngobit",
                    "Tigithi",
                    "Thingithu",
                    "Umande",
                    "Nanyuki",
                ],
                "Laikipia North": [
                    "Mukogodo East",
                    "Mukogodo West",
                    "Segera",
                    "Sosian",
                ],
                "Laikipia West": [
                    "Ol-Moran",
                    "Rumuruti Township",
                    "Githiga",
                    "Marmanet",
                    "Salama",
                ],
            },

        })

        KENYA_ADMIN.update({

            "Kakamega": {
                "Butere": [
                    "Marama West",
                    "Marama Central",
                    "Marama North",
                    "Marama South",
                    "Marama East",
                ],
                "Ikolomani": [
                    "Idakho South",
                    "Idakho East",
                    "Idakho North",
                ],
                "Khwisero": [
                    "Kisa North",
                    "Kisa East",
                    "Kisa West",
                    "Kisa Central",
                ],
                "Lugari": [
                    "Mautuma",
                    "Lugari",
                    "Lumakanda",
                    "Chekalini",
                    "Chevaywa",
                    "Lwandeti",
                ],
                "Lurambi": [
                    "Butali/Chegulo",
                    "Shirere",
                    "Mahiakalo",
                    "South Kabras",
                    "Central Kabras",
                ],
                "Malava": [
                    "West Kabras",
                    "East Kabras",
                    "Butali/Chegulo",
                    "South Kabras",
                    "Manda-Shivanga",
                ],
                "Matungu": [
                    "Koyonzo",
                    "Kholera",
                    "Khalaba",
                    "Mayoni",
                    "Namamali",
                ],
                "Mumias East": [
                    "Lusheya/Lubinu",
                    "Malaha/Isongo",
                ],
                "Mumias West": [
                    "Mumias Central",
                    "Mumias North",
                    "Etenje",
                    "Musanda",
                ],
                "Navakholo": [
                    "Ingostse-Mathia",
                    "Shinoyi-Shikomari",
                    "Bunyala West",
                    "Bunyala East",
                    "Bunyala Central",
                ],
            },

            "Kericho": {
                "Ainamoi": [
                    "Kapsoit",
                    "Ainamoi",
                    "Kipchebor",
                    "Kapkugerwet",
                    "Kapsaos",
                    "Kipchimchim",
                ],
                "Belgut": [
                    "Waldai",
                    "Kabianga",
                    "Cheptororiet/Seretut",
                    "Chaik",
                    "Kapsuser",
                ],
                "Bureti": [
                    "Kisiara",
                    "Tebesonik",
                    "Cheboin",
                    "Chemosot",
                    "Litein",
                ],
                "Kipkelion East": [
                    "Londiani",
                    "Kedowa/Kimugul",
                    "Chepseon",
                    "Tendeno/Sorget",
                ],
                "Kipkelion West": [
                    "Kunyak",
                    "Kamasian",
                    "Chilchila",
                ],
                "Sigowet/Soin": [
                    "Sigowet",
                    "Kaplelartet",
                    "Soliat",
                    "Soin",
                ],
            },

            "Kiambu": {
                "Gatundu North": [
                    "Gituamba",
                    "Githobokoni",
                    "Chania",
                    "Mang'u",
                ],
                "Gatundu South": [
                    "Kiamwangi",
                    "Kiganjo",
                    "Ndarugu",
                    "Ngenda",
                ],
                "Juja": [
                    "Murera",
                    "Theta",
                    "Juja",
                    "Witeithie",
                    "Kalimoni",
                ],
                "Kabete": [
                    "Gitaru",
                    "Muguga",
                    "Nyadhuna",
                    "Kabete",
                    "Uthiru",
                ],
                "Kiambaa": [
                    "Cianda",
                    "Karuri",
                    "Ndenderu",
                    "Muchatha",
                    "Kihara",
                ],
                "Kiambu": [
                    "Township",
                    "Riabai",
                    "Ndumberi",
                    "Ting'ang'a",
                ],
                "Kikuyu": [
                    "Karai",
                    "Nachu",
                    "Sigona",
                    "Kikuyu",
                ],
                "Lari": [
                    "Kinale",
                    "Kijabe",
                    "Nyanduma",
                    "Nyanduma",
                    "Kirenga",
                ],
                "Limuru": [
                    "Bibirioni",
                    "Limuru Central",
                    "Ndeiya",
                    "Limuru East",
                    "Ngecha Tigoni",
                ],
                "Ruiru": [
                    "Gitothua",
                    "Biashara",
                    "Gatongora",
                    "Kahawa Sukari",
                    "Kahawa Wendani",
                ],
                "Thika Town": [
                    "Township",
                    "Kamenu",
                    "Hospital",
                    "Gatuanyaga",
                    "Ngoliba",
                ],
            },

            "Kilifi": {
                "Ganze": [
                    "Ganze",
                    "Bamba",
                    "Jaribuni",
                    "Sokoke",
                ],
                "Kaloleni": [
                    "Kaloleni",
                    "Kayafungo",
                    "Mariakani",
                    "Mwanamwinga",
                ],
                "Kilifi North": [
                    "Tezo",
                    "Sokoni",
                    "Kibarani",
                    "Dabaso",
                    "Matsangoni",
                ],
                "Kilifi South": [
                    "Junju",
                    "Mwarakaya",
                    "Shimo La Tewa",
                    "Chasimba",
                ],
                "Magarini": [
                    "Marafa",
                    "Magarini",
                    "Gongoni",
                    "Adu",
                    "Garashi",
                    "Sabaki",
                ],
                "Malindi": [
                    "Jilore",
                    "Kakuyuni",
                    "Ganda",
                    "Shella",
                    "Township",
                ],
                "Rabai": [
                    "Rabai/Kisurutini",
                    "Mwawesa",
                    "Ruruma",
                    "Kambe/Ribe",
                ],
            },

            "Kirinyaga": {
                "Gichugu": [
                    "Kabare",
                    "Baragwi",
                    "Njukiini",
                    "Ngariama",
                    "Karumandi",
                ],
                "Kirinyaga Central": [
                    "Mutira",
                    "Kanyekini",
                    "Kerugoya",
                    "Inoi",
                ],
                "Mwea": [
                    "Mutithi",
                    "Kangai",
                    "Thiba",
                    "Wamumu",
                    "Nyangati",
                    "Murinduko",
                    "Gathigiriri",
                ],
                "Ndia": [
                    "Mukure",
                    "Kiine",
                    "Kariti",
                ],
            },

        })

        KENYA_ADMIN.update({

            "Embu": {
                "Manyatta": [
                    "Ruguru/Ngandori",
                    "Kithimu",
                    "Nginda",
                    "Mbeti North",
                    "Mbeti South",
                ],
                "Runyenjes": [
                    "Gaturi North",
                    "Gaturi South",
                    "Kagaari North",
                    "Kagaari South",
                    "Central Ward",
                ],
                "Mbeere North": [
                    "Nthawa",
                    "Muminji",
                    "Evurore",
                ],
                "Mbeere South": [
                    "Mwea",
                    "Makima",
                    "Kiambere",
                ],
            },

            "Garissa": {
                "Balambala": [
                    "Balambala",
                    "Danyere",
                    "Jara Jara",
                    "Saka",
                    "Sankuri",
                ],
                "Dadaab": [
                    "Dertu",
                    "Dadaab",
                    "Labasigale",
                    "Damajale",
                ],
                "Fafi": [
                    "Bura",
                    "Dekaharia",
                    "Jarajila",
                    "Fafi",
                    "Nanighi",
                ],
                "Garissa Township": [
                    "Waberi",
                    "Galbet",
                    "Township",
                    "Iftin",
                ],
                "Ijara": [
                    "Ijara",
                    "Hulugho",
                    "Sangailu",
                    "Masalani",
                ],
                "Lagdera": [
                    "Modogashe",
                    "Benane",
                    "Goreale",
                    "Maalimin",
                    "Sabena",
                ],
            },

            "Homa Bay": {
                "Homa Bay Town": [
                    "Homa Bay Central",
                    "Homa Bay Arujo",
                    "Homa Bay West",
                ],
                "Kabondo Kasipul": [
                    "Kabondo East",
                    "Kabondo West",
                    "Kasipul East",
                    "Kasipul West",
                ],
                "Karachuonyo": [
                    "West Karachuonyo",
                    "North Karachuonyo",
                    "Central",
                    "Kanyaluo",
                    "Kibiri",
                    "Wangchieng",
                    "Kendu Bay Town",
                ],
                "Kasipul": [
                    "West Kasipul",
                    "East Kasipul",
                    "Central Kasipul",
                    "South Kasipul",
                ],
                "Ndhiwa": [
                    "Kwabwai",
                    "Kanyikela",
                    "North Kabuoch",
                    "South Kabuoch",
                    "Kanyamwa Kologi",
                    "Kanyamwa Kosewe",
                ],
                "Rangwe": [
                    "Kochia",
                    "Gem West",
                    "Gem East",
                ],
                "Suba North": [
                    "Mfangano Island",
                    "Rusinga Island",
                    "Kasgunga",
                    "Gembe",
                ],
                "Suba South": [
                    "Gwassi North",
                    "Gwassi South",
                    "Kaksingri West",
                    "Kaksingri East",
                ],
            },

            "Isiolo": {
                "Isiolo North": [
                    "Wabera",
                    "Bulla Pesa",
                    "Chari",
                    "Cherab",
                    "Ngaremara",
                    "Burat",
                ],
                "Isiolo South": [
                    "Garbatulla",
                    "Kinna",
                    "Sericho",
                ],
            },

            "Kajiado": {
                "Kajiado Central": [
                    "Purko",
                    "Ildamat",
                    "Dalalekutuk",
                    "Matapato North",
                    "Matapato South",
                ],
                "Kajiado East": [
                    "Kitengela",
                    "Oloosirkon/Sholinke",
                    "Kenya/Township",
                    "Kaputiei North",
                ],
                "Kajiado North": [
                    "Olkeri",
                    "Ongata Rongai",
                    "Nkaimurunya",
                    "Ngong",
                    "Oloolua",
                ],
                "Kajiado South": [
                    "Entonet/Lenkisim",
                    "Mbirikani/Eselenkei",
                    "Kuku",
                    "Rombo",
                    "Kimana",
                ],
                "Kajiado West": [
                    "Keekonyokie",
                    "Iloodokilani",
                    "Magadi",
                    "Ewuaso Oonkidong'i",
                    "Mosiro",
                ],
            },

        })

        # Clear existing data
        # self.stdout.write('Clearing existing data...')
        # Wards.objects.all().delete()
        # Constituencies.objects.all().delete()
        # Counties.objects.all().delete()

        # Populate the database
        for county_name, constituencies in KENYA_ADMIN.items():
            # Create or get county
            county, created = Counties.objects.get_or_create(name=county_name)
            self.stdout.write(self.style.SUCCESS(f'Processing county: {county_name}'))
            
            for constituency_name, wards in constituencies.items():
                # Create or get constituency
                constituency, created = Constituencies.objects.get_or_create(
                    name=constituency_name,
                    county=county
                )
                self.stdout.write(f'  - Processing constituency: {constituency_name}')
                
                for ward_name in wards:
                    # Create or get ward
                    ward, created = Wards.objects.get_or_create(
                        name=ward_name,
                        constituency=constituency
                    )
                    self.stdout.write(f'    - Added ward: {ward_name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated Kenya administrative data!'))

"""
器官解剖结构配置文件
包含所有允许的器官和对应的解剖位置
"""

# 主要器官的详细解剖结构
ORGAN_ANATOMY_STRUCTURE = {
    "Heart (Cor)": [
        "Aortic Valve", "Mitral Valve", "Tricuspid Valve", "Pulmonary Valve",
        "Left Ventricle (LV)", "Right Ventricle (RV)", "Left Atrium (LA)", "Right Atrium (RA)",
        "Interventricular Septum (IVS)", "Interatrial Septum (IAS)", "Left Ventricular Posterior Wall (LVPW)",
        "Papillary Muscles", "Chordae Tendineae", "Aortic Root & Ascending Aorta",
        "Main Pulmonary Artery (MPA)", "Pericardium"
    ],
    "Liver (Hepar)": [
        "Left Lobe of Liver", "Right Lobe of Liver", "Caudate Lobe of Liver",
        "Portal Vein (Main, Left, and Right branches)", "Hepatic Veins (Left, Middle, and Right)",
        "Hepatic Artery", "Intrahepatic Bile Ducts", "Common Bile Duct (CBD)"
    ],
    "Kidney (Ren)": [
        "Renal Cortex", "Renal Medulla (Pyramids)", "Renal Pelvis",
        "Renal Calyces (Major & Minor)", "Renal Hilum"
    ],
    "Thyroid gland": [
        "Right Lobe of Thyroid", "Left Lobe of Thyroid", "Isthmus of Thyroid"
    ],
    "Pancreas": [
        "Head of the Pancreas", "Uncinate Process", "Neck of the Pancreas",
        "Body of the Pancreas", "Tail of the Pancreas", "Main Pancreatic Duct (Duct of Wirsung)"
    ]
}

# 允许的器官列表
ALLOWED_ORGANS = list(ORGAN_ANATOMY_STRUCTURE.keys()) + [
    "Brain", "Cerebellum", "Brainstem", "Diencephalon", "Spinal cord (Medulla spinalis)",
    "Artery (Arteria)", "Vein (Vena)", "Capillary (Vas capillare)",
    "Nose (Nasus)", "Pharynx", "Larynx", "Trachea", "Bronchus", "Lung (Pulmo)",
    "Mouth (Oral cavity)", "Tongue (Lingua)", "Teeth (Dentes)", "Salivary glands",
    "Esophagus", "Stomach (Gaster)", "Small intestine (Intestinum tenue)", "Large intestine (Intestinum crassum)",
    "Gallbladder (Vesica biliaris)", "Mesentery", "Ureter", "Urinary bladder (Vesica urinaria)", "Urethra",
    "Testis", "Epididymis", "Prostate", "Penis", "Ovary (Ovarium)", "Uterine tube (Tuba uterina)",
    "Uterus", "Vagina", "Vulva", "Placenta", "Pituitary gland (Hypophysis)", "Pineal gland",
    "Parathyroid gland", "Adrenal gland (Suprarenal gland)", "Thymus", "Lymph node",
    "Spleen (Lien)", "Tonsil (Tonsilla)", "Bone marrow (Medulla ossium)", "Eye (Oculus)",
    "Ear (Auris)", "Skin (Cutis)", "Mammary gland"
]

# 其他器官的解剖结构
ELSE_STRUCT = {
    "Brain": [
        "Cerebral Cortex", "Frontal Lobe", "Parietal Lobe", "Temporal Lobe", "Occipital Lobe",
        "Cerebellum", "Brainstem", "Medulla Oblongata", "Pons", "Midbrain",
        "Diencephalon", "Thalamus", "Hypothalamus", "Basal Ganglia", "Corpus Callosum",
        "Spinal cord (Medulla spinalis)", "Cerebrospinal Fluid (CSF)", "Meninges"
    ],
    "Artery (Arteria)": [
        "Aorta", "Ascending Aorta", "Aortic Arch", "Descending Aorta", "Thoracic Aorta", "Abdominal Aorta",
        "Coronary Artery", "Left Anterior Descending Artery (LAD)", "Circumflex Artery", "Right Coronary Artery",
        "Carotid Artery", "Internal Carotid Artery", "External Carotid Artery", "Common Carotid Artery",
        "Femoral Artery", "Brachial Artery", "Radial Artery", "Ulnar Artery", "Popliteal Artery"
    ],
    "Vein (Vena)": [
        "Superior Vena Cava", "Inferior Vena Cava", "Portal Vein", "Hepatic Veins", "Jugular Vein",
        "Internal Jugular Vein", "External Jugular Vein", "Subclavian Vein", "Brachiocephalic Vein",
        "Femoral Vein", "Popliteal Vein", "Great Saphenous Vein", "Small Saphenous Vein"
    ],
    "Capillary (Vas capillare)": [
        "Capillary Bed", "Microcirculation", "Arterioles", "Venules", "Capillary Network"
    ],
    "Nose (Nasus)": [
        "Nasal Cavity", "Nasal Septum", "Nasal Turbinates", "Superior Turbinate", "Middle Turbinate", "Inferior Turbinate",
        "Olfactory Epithelium", "Nasal Vestibule", "Nasal Conchae", "Sphenoid Sinus", "Frontal Sinus", "Maxillary Sinus", "Ethmoid Sinus"
    ],
    "Pharynx": [
        "Nasopharynx", "Oropharynx", "Laryngopharynx", "Pharyngeal Tonsils", "Palatine Tonsils", "Lingual Tonsils",
        "Pharyngeal Muscles", "Pharyngeal Constrictors", "Soft Palate", "Uvula"
    ],
    "Larynx": [
        "Vocal Cords", "True Vocal Cords", "False Vocal Cords", "Epiglottis", "Thyroid Cartilage", "Cricoid Cartilage",
        "Arytenoid Cartilages", "Corniculate Cartilages", "Cuneiform Cartilages", "Laryngeal Vestibule", "Laryngeal Ventricle"
    ],
    "Trachea": [
        "Tracheal Rings", "Carina", "Tracheal Bifurcation", "Tracheal Cartilage", "Tracheal Membrane", "Tracheal Mucosa"
    ],
    "Bronchus": [
        "Main Bronchi", "Left Main Bronchus", "Right Main Bronchus", "Lobar Bronchi", "Segmental Bronchi", "Bronchioles",
        "Terminal Bronchioles", "Respiratory Bronchioles", "Bronchial Tree"
    ],
    "Lung (Pulmo)": [
        "Left Lung", "Right Lung", "Lung Lobes", "Superior Lobe", "Middle Lobe", "Inferior Lobe",
        "Alveoli", "Alveolar Sacs", "Alveolar Ducts", "Pleura", "Visceral Pleura", "Parietal Pleura",
        "Pleural Cavity", "Lung Hilum", "Bronchopulmonary Segments"
    ],
    "Mouth (Oral cavity)": [
        "Oral Mucosa", "Hard Palate", "Soft Palate", "Uvula", "Oral Vestibule", "Oral Cavity Proper",
        "Palatine Tonsils", "Palatoglossal Arch", "Palatopharyngeal Arch", "Frenulum of Tongue"
    ],
    "Tongue (Lingua)": [
        "Tongue Body", "Tongue Root", "Tongue Tip", "Lingual Papillae", "Filiform Papillae", "Fungiform Papillae",
        "Circumvallate Papillae", "Foliate Papillae", "Lingual Tonsils", "Lingual Frenulum", "Lingual Muscles"
    ],
    "Teeth (Dentes)": [
        "Incisors", "Canines", "Premolars", "Molars", "Dental Enamel", "Dental Pulp", "Dental Crown", "Dental Root",
        "Dental Cementum", "Dental Dentin", "Periodontal Ligament", "Dental Alveoli", "Gingiva"
    ],
    "Salivary glands": [
        "Parotid Gland", "Submandibular Gland", "Sublingual Gland", "Minor Salivary Glands", "Salivary Ducts",
        "Parotid Duct", "Submandibular Duct", "Sublingual Duct"
    ],
    "Esophagus": [
        "Esophageal Body", "Esophageal Sphincter", "Upper Esophageal Sphincter", "Lower Esophageal Sphincter",
        "Esophageal Mucosa", "Esophageal Submucosa", "Esophageal Muscularis", "Esophageal Adventitia",
        "Esophageal Hiatus", "Esophageal Varices"
    ],
    "Stomach (Gaster)": [
        "Gastric Fundus", "Gastric Body", "Gastric Antrum", "Pylorus", "Gastric Mucosa", "Gastric Rugae",
        "Gastric Pits", "Gastric Glands", "Parietal Cells", "Chief Cells", "Gastric Cardia", "Gastric Lesser Curvature",
        "Gastric Greater Curvature", "Gastric Omentum"
    ],
    "Small intestine (Intestinum tenue)": [
        "Duodenum", "Jejunum", "Ileum", "Intestinal Villi", "Intestinal Mucosa", "Intestinal Submucosa",
        "Intestinal Muscularis", "Intestinal Serosa", "Peyer's Patches", "Intestinal Crypts", "Brunner's Glands",
        "Duodenal Papilla", "Major Duodenal Papilla", "Minor Duodenal Papilla"
    ],
    "Large intestine (Intestinum crassum)": [
        "Cecum", "Colon", "Ascending Colon", "Transverse Colon", "Descending Colon", "Sigmoid Colon",
        "Rectum", "Anal Canal", "Colonic Mucosa", "Colonic Haustra", "Colonic Taeniae", "Colonic Appendices Epiploicae",
        "Ileocecal Valve", "Anal Sphincters", "Internal Anal Sphincter", "External Anal Sphincter"
    ],
    "Gallbladder (Vesica biliaris)": [
        "Gallbladder Fundus", "Gallbladder Body", "Gallbladder Neck", "Gallbladder Wall", "Cystic Duct",
        "Gallbladder Mucosa", "Gallbladder Muscularis", "Gallbladder Serosa", "Hartmann's Pouch"
    ],
    "Mesentery": [
        "Mesenteric Root", "Mesenteric Fat", "Mesenteric Vessels", "Mesenteric Lymph Nodes", "Mesenteric Arteries",
        "Mesenteric Veins", "Mesenteric Nerves", "Mesenteric Peritoneum"
    ],
    "Ureter": [
        "Proximal Ureter", "Mid Ureter", "Distal Ureter", "Ureteral Orifice", "Ureteral Wall", "Ureteral Mucosa",
        "Ureteral Muscularis", "Ureteral Adventitia", "Ureteral Pelvis", "Uretero-vesical Junction"
    ],
    "Urinary bladder (Vesica urinaria)": [
        "Bladder Wall", "Trigone of the Bladder", "Bladder Neck", "Urethral Orifice", "Bladder Dome", "Bladder Base",
        "Bladder Mucosa", "Bladder Muscularis", "Bladder Adventitia", "Detrusor Muscle", "Bladder Urethra"
    ],
    "Urethra": [
        "Prostatic Urethra", "Membranous Urethra", "Spongy Urethra", "Urethral Meatus", "Urethral Mucosa",
        "Urethral Glands", "Bulbourethral Glands", "Urethral Sphincters"
    ],
    "Testis": [
        "Testicular Parenchyma", "Seminiferous Tubules", "Epididymis", "Spermatic Cord", "Testicular Capsule",
        "Tunica Albuginea", "Tunica Vaginalis", "Testicular Septa", "Testicular Lobules", "Sertoli Cells",
        "Leydig Cells", "Testicular Blood Vessels", "Testicular Nerves"
    ],
    "Epididymis": [
        "Epididymal Head", "Epididymal Body", "Epididymal Tail", "Epididymal Duct", "Epididymal Tubules",
        "Epididymal Epithelium", "Epididymal Smooth Muscle"
    ],
    "Prostate": [
        "Prostate Gland", "Prostatic Urethra", "Prostatic Capsule", "Prostatic Lobes", "Peripheral Zone",
        "Central Zone", "Transition Zone", "Anterior Fibromuscular Stroma", "Prostatic Ducts", "Prostatic Acini"
    ],
    "Penis": [
        "Penile Shaft", "Glans Penis", "Corpus Cavernosum", "Corpus Spongiosum", "Penile Urethra", "Penile Skin",
        "Foreskin", "Penile Frenulum", "Penile Septum", "Penile Blood Vessels", "Penile Nerves"
    ],
    "Ovary (Ovarium)": [
        "Ovarian Cortex", "Ovarian Medulla", "Ovarian Follicles", "Corpus Luteum", "Corpus Albicans", "Ovarian Stroma",
        "Ovarian Blood Vessels", "Ovarian Ligaments", "Ovarian Surface Epithelium", "Ovarian Hilum"
    ],
    "Uterine tube (Tuba uterina)": [
        "Fallopian Tube", "Fimbriae", "Ampulla", "Isthmus", "Infundibulum", "Fallopian Tube Mucosa",
        "Fallopian Tube Muscularis", "Fallopian Tube Serosa", "Fallopian Tube Epithelium"
    ],
    "Uterus": [
        "Uterine Body", "Uterine Fundus", "Uterine Cervix", "Endometrium", "Myometrium", "Uterine Cavity",
        "Uterine Ligaments", "Uterine Blood Vessels", "Uterine Nerves", "Uterine Peritoneum"
    ],
    "Vagina": [
        "Vaginal Canal", "Vaginal Fornix", "Vaginal Mucosa", "Vaginal Wall", "Vaginal Epithelium", "Vaginal Muscles",
        "Vaginal Blood Vessels", "Vaginal Nerves", "Vaginal Vestibule", "Vaginal Introitus"
    ],
    "Vulva": [
        "Labia Majora", "Labia Minora", "Clitoris", "Vestibule", "Vestibular Glands", "Bartholin's Glands",
        "Skene's Glands", "Mons Pubis", "Perineum", "Vulvar Skin", "Vulvar Mucosa"
    ],
    "Placenta": [
        "Placental Disc", "Umbilical Cord", "Chorionic Villi", "Placental Lobes", "Placental Blood Vessels",
        "Placental Membranes", "Amniotic Membrane", "Chorionic Membrane", "Placental Septa", "Placental Sinusoids"
    ],
    "Pituitary gland (Hypophysis)": [
        "Anterior Pituitary", "Posterior Pituitary", "Pituitary Stalk", "Pituitary Gland", "Adenohypophysis",
        "Neurohypophysis", "Pituitary Blood Vessels", "Pituitary Nerves", "Pituitary Hormones"
    ],
    "Pineal gland": [
        "Pineal Parenchyma", "Pinealocytes", "Pineal Blood Vessels", "Pineal Nerves", "Pineal Hormones",
        "Pineal Calcifications", "Pineal Recess"
    ],
    "Parathyroid gland": [
        "Parathyroid Chief Cells", "Parathyroid Oxyphil Cells", "Parathyroid Blood Vessels", "Parathyroid Nerves",
        "Parathyroid Hormones", "Parathyroid Capsule"
    ],
    "Adrenal gland (Suprarenal gland)": [
        "Adrenal Cortex", "Adrenal Medulla", "Adrenal Capsule", "Zona Glomerulosa", "Zona Fasciculata",
        "Zona Reticularis", "Adrenal Blood Vessels", "Adrenal Nerves", "Adrenal Hormones"
    ],
    "Thymus": [
        "Thymic Cortex", "Thymic Medulla", "Thymic Lobules", "Thymic Epithelial Cells", "Thymocytes",
        "Thymic Blood Vessels", "Thymic Nerves", "Thymic Hormones", "Thymic Hassall's Corpuscles"
    ],
    "Lymph node": [
        "Lymph Node Cortex", "Lymph Node Medulla", "Lymph Node Sinuses", "Lymph Node Follicles", "Lymph Node Capsule",
        "Lymph Node Trabeculae", "Lymph Node Blood Vessels", "Lymph Node Nerves", "Lymph Node Lymphocytes"
    ],
    "Spleen (Lien)": [
        "Splenic Pulp", "Splenic Capsule", "Splenic Trabeculae", "White Pulp", "Red Pulp", "Splenic Follicles",
        "Splenic Blood Vessels", "Splenic Nerves", "Splenic Sinusoids", "Splenic Cords"
    ],
    "Tonsil (Tonsilla)": [
        "Palatine Tonsils", "Pharyngeal Tonsils", "Lingual Tonsils", "Tonsillar Crypts", "Tonsillar Epithelium",
        "Tonsillar Lymphocytes", "Tonsillar Blood Vessels", "Tonsillar Nerves", "Tonsillar Capsule"
    ],
    "Bone marrow (Medulla ossium)": [
        "Red Bone Marrow", "Yellow Bone Marrow", "Hematopoietic Tissue", "Bone Marrow Stroma", "Bone Marrow Sinusoids",
        "Bone Marrow Blood Vessels", "Bone Marrow Nerves", "Bone Marrow Cells", "Bone Marrow Matrix"
    ],
    "Eye (Oculus)": [
        "Cornea", "Iris", "Lens", "Retina", "Optic Nerve", "Sclera", "Choroid", "Ciliary Body", "Vitreous Humor",
        "Aqueous Humor", "Conjunctiva", "Eyelids", "Eyelashes", "Lacrimal Glands", "Extraocular Muscles"
    ],
    "Ear (Auris)": [
        "External Ear", "Middle Ear", "Inner Ear", "Cochlea", "Vestibular System", "Eardrum", "Ossicles",
        "Eustachian Tube", "Semicircular Canals", "Vestibule", "Auditory Nerve", "Ear Canal", "Auricle"
    ],
    "Skin (Cutis)": [
        "Epidermis", "Dermis", "Subcutaneous Tissue", "Hair Follicles", "Sebaceous Glands", "Sweat Glands",
        "Melanocytes", "Keratinocytes", "Dermal Papillae", "Dermal Blood Vessels", "Dermal Nerves", "Stratum Corneum"
    ],
    "Mammary gland": [
        "Mammary Lobules", "Mammary Ducts", "Nipple", "Areola", "Mammary Fat", "Mammary Blood Vessels",
        "Mammary Nerves", "Mammary Lymphatics", "Mammary Stroma", "Mammary Epithelium"
    ]
}

# 器官映射配置
ORGAN_MAPPING = {
    # Brain related
    "brain": "Brain", "cerebral": "Brain", "cerebrum": "Brain", "cortical": "Brain",
    "cerebellum": "Cerebellum", "cerebellar": "Cerebellum",
    "brainstem": "Brainstem", "brain stem": "Brainstem", "medulla": "Brainstem", "pons": "Brainstem", "midbrain": "Brainstem",
    "diencephalon": "Diencephalon", "diencephalic": "Diencephalon", "thalamus": "Diencephalon", "hypothalamus": "Diencephalon",
    "spinal cord": "Spinal cord (Medulla spinalis)", "medulla spinalis": "Spinal cord (Medulla spinalis)", "spinal": "Spinal cord (Medulla spinalis)",
    
    # Heart related
    "heart": "Heart (Cor)", "cardiac": "Heart (Cor)", "myocardium": "Heart (Cor)", "coronary": "Heart (Cor)",
    "aortic": "Heart (Cor)", "mitral": "Heart (Cor)", "tricuspid": "Heart (Cor)", "pulmonic": "Heart (Cor)",
    "atria": "Heart (Cor)", "ventricle": "Heart (Cor)", "septum": "Heart (Cor)", "pericardium": "Heart (Cor)", "cor": "Heart (Cor)",
    
    # Vascular system
    "artery": "Artery (Arteria)", "arterial": "Artery (Arteria)", "arteria": "Artery (Arteria)", "aorta": "Artery (Arteria)",
    "vein": "Vein (Vena)", "venous": "Vein (Vena)", "vena": "Vein (Vena)", "vena cava": "Vein (Vena)",
    "capillary": "Capillary (Vas capillare)", "capillaries": "Capillary (Vas capillare)", "vas capillare": "Capillary (Vas capillare)",
    
    # Respiratory system
    "nose": "Nose (Nasus)", "nasal": "Nose (Nasus)", "nasus": "Nose (Nasus)", "sinus": "Nose (Nasus)",
    "pharynx": "Pharynx", "pharyngeal": "Pharynx", "throat": "Pharynx",
    "larynx": "Larynx", "laryngeal": "Larynx", "voice box": "Larynx",
    "trachea": "Trachea", "tracheal": "Trachea", "windpipe": "Trachea",
    "bronchus": "Bronchus", "bronchi": "Bronchus", "bronchial": "Bronchus", "bronchioles": "Bronchus",
    "lung": "Lung (Pulmo)", "pulmonary": "Lung (Pulmo)", "pulmo": "Lung (Pulmo)", "lungs": "Lung (Pulmo)",
    
    # Digestive system - Oral
    "mouth": "Mouth (Oral cavity)", "oral": "Mouth (Oral cavity)", "oral cavity": "Mouth (Oral cavity)",
    "tongue": "Tongue (Lingua)", "lingual": "Tongue (Lingua)", "lingua": "Tongue (Lingua)",
    "teeth": "Teeth (Dentes)", "dental": "Teeth (Dentes)", "dentes": "Teeth (Dentes)", "tooth": "Teeth (Dentes)",
    "salivary": "Salivary glands", "salivary gland": "Salivary glands", "parotid": "Salivary glands", "submandibular": "Salivary glands",
    
    # Digestive system - GI tract
    "esophagus": "Esophagus", "esophageal": "Esophagus", "oesophagus": "Esophagus",
    "stomach": "Stomach (Gaster)", "gastric": "Stomach (Gaster)", "gaster": "Stomach (Gaster)",
    "small intestine": "Small intestine (Intestinum tenue)", "intestinum tenue": "Small intestine (Intestinum tenue)", "duodenum": "Small intestine (Intestinum tenue)", "jejunum": "Small intestine (Intestinum tenue)", "ileum": "Small intestine (Intestinum tenue)",
    "large intestine": "Large intestine (Intestinum crassum)", "intestinum crassum": "Large intestine (Intestinum crassum)", "colon": "Large intestine (Intestinum crassum)", "rectum": "Large intestine (Intestinum crassum)", "cecum": "Large intestine (Intestinum crassum)",
    "liver": "Liver (Hepar)", "hepatic": "Liver (Hepar)", "hepar": "Liver (Hepar)",
    "gallbladder": "Gallbladder (Vesica biliaris)", "vesica biliaris": "Gallbladder (Vesica biliaris)", "gall bladder": "Gallbladder (Vesica biliaris)",
    "pancreas": "Pancreas", "pancreatic": "Pancreas",
    "mesentery": "Mesentery", "mesenteric": "Mesentery",
    
    # Urinary system
    "kidney": "Kidney (Ren)", "renal": "Kidney (Ren)", "ren": "Kidney (Ren)", "kidneys": "Kidney (Ren)",
    "ureter": "Ureter", "ureteral": "Ureter", "ureters": "Ureter",
    "urinary bladder": "Urinary bladder (Vesica urinaria)", "bladder": "Urinary bladder (Vesica urinaria)", "vesica urinaria": "Urinary bladder (Vesica urinaria)",
    "urethra": "Urethra", "urethral": "Urethra",
    
    # Reproductive system - Male
    "testis": "Testis", "testicle": "Testis", "testicular": "Testis", "testes": "Testis",
    "epididymis": "Epididymis", "epididymal": "Epididymis",
    "prostate": "Prostate", "prostatic": "Prostate",
    "penis": "Penis", "penile": "Penis",
    
    # Reproductive system - Female
    "ovary": "Ovary (Ovarium)", "ovarian": "Ovary (Ovarium)", "ovarium": "Ovary (Ovarium)", "ovaries": "Ovary (Ovarium)",
    "uterine tube": "Uterine tube (Tuba uterina)", "fallopian tube": "Uterine tube (Tuba uterina)", "tuba uterina": "Uterine tube (Tuba uterina)", "oviduct": "Uterine tube (Tuba uterina)",
    "uterus": "Uterus", "uterine": "Uterus", "womb": "Uterus",
    "vagina": "Vagina", "vaginal": "Vagina",
    "vulva": "Vulva", "vulvar": "Vulva",
    "placenta": "Placenta", "placental": "Placenta",
    
    # Endocrine system
    "pituitary": "Pituitary gland (Hypophysis)", "pituitary gland": "Pituitary gland (Hypophysis)", "hypophysis": "Pituitary gland (Hypophysis)", "hypophyseal": "Pituitary gland (Hypophysis)",
    "pineal": "Pineal gland", "pineal gland": "Pineal gland", "pineal body": "Pineal gland",
    "thyroid": "Thyroid gland", "thyroid gland": "Thyroid gland", "thyroidal": "Thyroid gland",
    "parathyroid": "Parathyroid gland", "parathyroid gland": "Parathyroid gland", "parathyroidal": "Parathyroid gland",
    "adrenal": "Adrenal gland (Suprarenal gland)", "adrenal gland": "Adrenal gland (Suprarenal gland)", "suprarenal": "Adrenal gland (Suprarenal gland)", "suprarenal gland": "Adrenal gland (Suprarenal gland)",
    
    # Immune system
    "thymus": "Thymus", "thymic": "Thymus",
    "lymph node": "Lymph node", "lymph nodes": "Lymph node", "lymphatic": "Lymph node",
    "spleen": "Spleen (Lien)", "splenic": "Spleen (Lien)", "lien": "Spleen (Lien)",
    "tonsil": "Tonsil (Tonsilla)", "tonsils": "Tonsil (Tonsilla)", "tonsilla": "Tonsil (Tonsilla)", "tonsillar": "Tonsil (Tonsilla)",
    "bone marrow": "Bone marrow (Medulla ossium)", "medulla ossium": "Bone marrow (Medulla ossium)", "marrow": "Bone marrow (Medulla ossium)",
    
    # Sensory organs
    "eye": "Eye (Oculus)", "ocular": "Eye (Oculus)", "oculus": "Eye (Oculus)", "eyes": "Eye (Oculus)",
    "ear": "Ear (Auris)", "auricular": "Ear (Auris)", "auris": "Ear (Auris)", "ears": "Ear (Auris)",
    
    # Integumentary system
    "skin": "Skin (Cutis)", "cutaneous": "Skin (Cutis)", "cutis": "Skin (Cutis)", "dermal": "Skin (Cutis)",
    "mammary": "Mammary gland", "mammary gland": "Mammary gland", "breast": "Mammary gland", "breasts": "Mammary gland"
}

def get_anatomical_locations(organ_name: str) -> list:
    """根据器官名称获取对应的解剖位置列表"""
    if organ_name in ORGAN_ANATOMY_STRUCTURE:
        return ORGAN_ANATOMY_STRUCTURE[organ_name]
    elif organ_name in ELSE_STRUCT:
        return ELSE_STRUCT[organ_name]
    else:
        return []

def is_valid_organ(organ_name: str) -> bool:
    """检查器官名称是否有效"""
    return organ_name in ALLOWED_ORGANS

def map_organ_name(keyword: str) -> str:
    """根据关键词映射到标准器官名称"""
    keyword_lower = keyword.lower()
    return ORGAN_MAPPING.get(keyword_lower, keyword)

"""Drug reference mapping module.

Provides the :class:`MedicineMapper` which loads a CSV-based drug
reference and maps brand names to generic names, looks up drug
categories, and validates medicine names.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MedicineMapper:
    """Maps brand-name drugs to their generic equivalents and categories.

    Parameters
    ----------
    reference_path : str, optional
        Path to ``drug_reference.csv`` with columns
        ``brand_name``, ``generic_name``, and ``category``.
    """

    def __init__(self, reference_path: Optional[str] = None) -> None:
        # brand (upper) → {generic, category, purpose, dose_forms, strengths}
        self._brand_map: dict[str, dict[str, str]] = {}
        # generic (upper) → category
        self._generic_map: dict[str, str] = {}
        # All known names (upper) for quick membership tests
        self._all_names: set[str] = set()
        # Full drug details (generic_name upper) -> dict of all official attributes
        self._drug_details: dict[str, dict[str, Any]] = {}

        # Built-in reference covering the most common drugs seen in
        # Indian discharge summaries.
        self._load_builtin()

        if reference_path:
            self.load_reference(reference_path)

    # ------------------------------------------------------------------
    # Built-in drug reference
    # ------------------------------------------------------------------

    def _load_builtin(self) -> None:
        """Populate the mapper with a built-in drug reference table."""
        builtin: list[tuple[str, str, str]] = [
            # (brand_name, generic_name, category)
            # --- Cardiovascular ---
            ("Ecosprin", "Aspirin", "Antiplatelet"),
            ("Disprin", "Aspirin", "Antiplatelet"),
            ("Clopivas", "Clopidogrel", "Antiplatelet"),
            ("Plavix", "Clopidogrel", "Antiplatelet"),
            ("Deplatt", "Clopidogrel", "Antiplatelet"),
            ("Clopilet", "Clopidogrel", "Antiplatelet"),
            ("Atorva", "Atorvastatin", "Statin"),
            ("Lipitor", "Atorvastatin", "Statin"),
            ("Tonact", "Atorvastatin", "Statin"),
            ("Storvas", "Atorvastatin", "Statin"),
            ("Rosuvas", "Rosuvastatin", "Statin"),
            ("Crestor", "Rosuvastatin", "Statin"),
            ("Rozavel", "Rosuvastatin", "Statin"),
            ("Rosulip", "Rosuvastatin", "Statin"),
            ("Telma", "Telmisartan", "ARB"),
            ("Telmikind", "Telmisartan", "ARB"),
            ("Telsar", "Telmisartan", "ARB"),
            ("Telsartan", "Telmisartan", "ARB"),
            ("Telma-H", "Telmisartan + Hydrochlorothiazide", "ARB + Diuretic"),
            ("Amlong", "Amlodipine", "CCB"),
            ("Norvasc", "Amlodipine", "CCB"),
            ("Amlokind", "Amlodipine", "CCB"),
            ("Stamlo", "Amlodipine", "CCB"),
            ("Amtas", "Amlodipine", "CCB"),
            ("Envas", "Enalapril", "ACE Inhibitor"),
            ("Enalapril", "Enalapril", "ACE Inhibitor"),
            ("Ramipril", "Ramipril", "ACE Inhibitor"),
            ("Cardace", "Ramipril", "ACE Inhibitor"),
            ("Ramistar", "Ramipril", "ACE Inhibitor"),
            ("Hopace", "Ramipril", "ACE Inhibitor"),
            ("Losartan", "Losartan", "ARB"),
            ("Losacar", "Losartan", "ARB"),
            ("Losar", "Losartan", "ARB"),
            ("Repace", "Losartan", "ARB"),
            ("Olmesar", "Olmesartan", "ARB"),
            ("Metolar", "Metoprolol", "Beta Blocker"),
            ("Betaloc", "Metoprolol", "Beta Blocker"),
            ("Concor", "Bisoprolol", "Beta Blocker"),
            ("Nebula", "Nebivolol", "Beta Blocker"),
            ("Nebicard", "Nebivolol", "Beta Blocker"),
            ("Nebilong", "Nebivolol", "Beta Blocker"),
            ("Cardivas", "Carvedilol", "Beta Blocker"),
            ("Dilzem", "Diltiazem", "CCB"),
            ("Nicardia", "Nifedipine", "CCB"),
            ("Depin", "Nifedipine", "CCB"),
            ("Lasix", "Furosemide", "Loop Diuretic"),
            ("Fruselac", "Furosemide", "Loop Diuretic"),
            ("Dytor", "Torsemide", "Loop Diuretic"),
            ("Aldactone", "Spironolactone", "Potassium-sparing Diuretic"),
            ("Spiromide", "Spironolactone", "Potassium-sparing Diuretic"),
            ("Lasilactone", "Furosemide + Spironolactone", "Diuretic Combination"),
            ("Hydrochlorothiazide", "Hydrochlorothiazide", "Thiazide Diuretic"),
            ("Acitrom", "Acenocoumarol", "Anticoagulant"),
            ("Warfarin", "Warfarin", "Anticoagulant"),
            ("Warf", "Warfarin", "Anticoagulant"),
            ("Clexane", "Enoxaparin", "Anticoagulant"),
            ("Lovenox", "Enoxaparin", "Anticoagulant"),
            ("Xarelto", "Rivaroxaban", "Anticoagulant"),
            ("Eliquis", "Apixaban", "Anticoagulant"),
            ("Pradaxa", "Dabigatran", "Anticoagulant"),
            ("Nitroglycerin", "Nitroglycerin", "Nitrate"),
            ("Sorbitrate", "Isosorbide Dinitrate", "Nitrate"),
            ("Imdur", "Isosorbide Mononitrate", "Nitrate"),
            ("Digoxin", "Digoxin", "Cardiac Glycoside"),
            ("Lanoxin", "Digoxin", "Cardiac Glycoside"),
            ("Amiodarone", "Amiodarone", "Antiarrhythmic"),
            ("Cordarone", "Amiodarone", "Antiarrhythmic"),

            # --- Diabetes ---
            ("Glycomet", "Metformin", "Biguanide"),
            ("Glucophage", "Metformin", "Biguanide"),
            ("Metsmall", "Metformin", "Biguanide"),
            ("Obimet", "Metformin", "Biguanide"),
            ("Amaryl", "Glimepiride", "Sulfonylurea"),
            ("Glimisave", "Glimepiride", "Sulfonylurea"),
            ("Glimy", "Glimepiride", "Sulfonylurea"),
            ("Glynase", "Glipizide", "Sulfonylurea"),
            ("Daonil", "Glibenclamide", "Sulfonylurea"),
            ("Galvus", "Vildagliptin", "DPP-4 Inhibitor"),
            ("Jalra", "Vildagliptin", "DPP-4 Inhibitor"),
            ("Januvia", "Sitagliptin", "DPP-4 Inhibitor"),
            ("Istavel", "Sitagliptin", "DPP-4 Inhibitor"),
            ("Trajenta", "Linagliptin", "DPP-4 Inhibitor"),
            ("Onglyza", "Saxagliptin", "DPP-4 Inhibitor"),
            ("Teneligliptin", "Teneligliptin", "DPP-4 Inhibitor"),
            ("Ziten", "Teneligliptin", "DPP-4 Inhibitor"),
            ("Forxiga", "Dapagliflozin", "SGLT2 Inhibitor"),
            ("Jardiance", "Empagliflozin", "SGLT2 Inhibitor"),
            ("Invokana", "Canagliflozin", "SGLT2 Inhibitor"),
            ("Voglibose", "Voglibose", "Alpha-glucosidase Inhibitor"),
            ("Pioglitazone", "Pioglitazone", "Thiazolidinedione"),
            ("Pioz", "Pioglitazone", "Thiazolidinedione"),
            ("Gluformin", "Metformin", "Biguanide"),
            ("Glyciphage", "Metformin", "Biguanide"),
            ("Gluconorm", "Repaglinide", "Meglitinide"),
            ("Ryzodeg", "Insulin Degludec + Aspart", "Insulin"),
            ("Lantus", "Insulin Glargine", "Insulin"),
            ("Basalog", "Insulin Glargine", "Insulin"),
            ("Toujeo", "Insulin Glargine", "Insulin"),
            ("Tresiba", "Insulin Degludec", "Insulin"),
            ("Novorapid", "Insulin Aspart", "Insulin"),
            ("Humalog", "Insulin Lispro", "Insulin"),
            ("Actrapid", "Human Insulin Regular", "Insulin"),
            ("Huminsulin", "Human Insulin", "Insulin"),
            ("Mixtard", "Biphasic Insulin", "Insulin"),
            ("Novomix", "Biphasic Insulin Aspart", "Insulin"),
            ("Apidra", "Insulin Glulisine", "Insulin"),
            ("Levemir", "Insulin Detemir", "Insulin"),

            # --- GI ---
            ("Pantop", "Pantoprazole", "PPI"),
            ("Pan", "Pantoprazole", "PPI"),
            ("Pan-D", "Pantoprazole + Domperidone", "PPI + Prokinetic"),
            ("Pantocid", "Pantoprazole", "PPI"),
            ("Nexpro", "Esomeprazole", "PPI"),
            ("Nexium", "Esomeprazole", "PPI"),
            ("Omez", "Omeprazole", "PPI"),
            ("Prilosec", "Omeprazole", "PPI"),
            ("Rablet", "Rabeprazole", "PPI"),
            ("Razo", "Rabeprazole", "PPI"),
            ("Sucrafil", "Sucralfate", "Mucosal Protectant"),
            ("Mucaine", "Aluminium Hydroxide + Magnesium Hydroxide + Oxethazaine", "Antacid"),
            ("Gelusil", "Antacid Gel", "Antacid"),
            ("Emeset", "Ondansetron", "Antiemetic"),
            ("Ondem", "Ondansetron", "Antiemetic"),
            ("Zofran", "Ondansetron", "Antiemetic"),
            ("Perinorm", "Metoclopramide", "Prokinetic"),
            ("Domstal", "Domperidone", "Prokinetic"),
            ("Duphalac", "Lactulose", "Osmotic Laxative"),
            ("Cremaffin", "Liquid Paraffin + Milk of Magnesia", "Laxative"),
            ("Loperamide", "Loperamide", "Antidiarrheal"),
            ("Imodium", "Loperamide", "Antidiarrheal"),
            ("Norflox-TZ", "Norfloxacin + Tinidazole", "Antibiotic + Antiprotozoal"),
            ("Rifagut", "Rifaximin", "Antibiotic"),
            ("Udiliv", "Ursodeoxycholic Acid", "Hepatoprotective"),

            # --- Pain / Anti-inflammatory ---
            ("Dolo", "Paracetamol", "Analgesic"),
            ("Calpol", "Paracetamol", "Analgesic"),
            ("Crocin", "Paracetamol", "Analgesic"),
            ("Paracetamol", "Paracetamol", "Analgesic"),
            ("Combiflam", "Ibuprofen + Paracetamol", "NSAID + Analgesic"),
            ("Brufen", "Ibuprofen", "NSAID"),
            ("Ibuprofen", "Ibuprofen", "NSAID"),
            ("Voveran", "Diclofenac", "NSAID"),
            ("Diclofenac", "Diclofenac", "NSAID"),
            ("Zerodol", "Aceclofenac", "NSAID"),
            ("Hifenac", "Aceclofenac", "NSAID"),
            ("Piroxicam", "Piroxicam", "NSAID"),
            ("Naprosyn", "Naproxen", "NSAID"),
            ("Naproxen", "Naproxen", "NSAID"),
            ("Etoricoxib", "Etoricoxib", "COX-2 Inhibitor"),
            ("Nucoxia", "Etoricoxib", "COX-2 Inhibitor"),
            ("Celecoxib", "Celecoxib", "COX-2 Inhibitor"),
            ("Tramadol", "Tramadol", "Opioid Analgesic"),
            ("Ultracet", "Tramadol + Paracetamol", "Opioid + Analgesic"),
            ("Pregabalin", "Pregabalin", "Neuropathic Pain"),
            ("Lyrica", "Pregabalin", "Neuropathic Pain"),
            ("Pregalin", "Pregabalin", "Neuropathic Pain"),
            ("Gabapentin", "Gabapentin", "Neuropathic Pain"),
            ("Gabantin", "Gabapentin", "Neuropathic Pain"),
            ("Gabapin", "Gabapentin", "Neuropathic Pain"),

            # --- Antibiotics ---
            ("Augmentin", "Amoxicillin + Clavulanate", "Antibiotic"),
            ("Moxclav", "Amoxicillin + Clavulanate", "Antibiotic"),
            ("Amoxyclav", "Amoxicillin + Clavulanate", "Antibiotic"),
            ("Amoxicillin", "Amoxicillin", "Antibiotic"),
            ("Azithral", "Azithromycin", "Antibiotic"),
            ("Zithromax", "Azithromycin", "Antibiotic"),
            ("Azee", "Azithromycin", "Antibiotic"),
            ("Ciplox", "Ciprofloxacin", "Antibiotic"),
            ("Cipro", "Ciprofloxacin", "Antibiotic"),
            ("Taxim", "Cefotaxime", "Antibiotic"),
            ("Monocef", "Ceftriaxone", "Antibiotic"),
            ("Ceftriaxone", "Ceftriaxone", "Antibiotic"),
            ("Cefixime", "Cefixime", "Antibiotic"),
            ("Zifi", "Cefixime", "Antibiotic"),
            ("Cephalexin", "Cephalexin", "Antibiotic"),
            ("Sporidex", "Cephalexin", "Antibiotic"),
            ("Meropenem", "Meropenem", "Antibiotic"),
            ("Merocrit", "Meropenem", "Antibiotic"),
            ("Piperacillin", "Piperacillin + Tazobactam", "Antibiotic"),
            ("Tazact", "Piperacillin + Tazobactam", "Antibiotic"),
            ("Levofloxacin", "Levofloxacin", "Antibiotic"),
            ("Levoflox", "Levofloxacin", "Antibiotic"),
            ("Tavanic", "Levofloxacin", "Antibiotic"),
            ("Linezolid", "Linezolid", "Antibiotic"),
            ("Lizolid", "Linezolid", "Antibiotic"),
            ("Doxycycline", "Doxycycline", "Antibiotic"),
            ("Metronidazole", "Metronidazole", "Antibiotic"),
            ("Flagyl", "Metronidazole", "Antibiotic"),
            ("Fluconazole", "Fluconazole", "Antifungal"),
            ("Flucos", "Fluconazole", "Antifungal"),

            # --- Respiratory ---
            ("Deriphyllin", "Etophylline + Theophylline", "Bronchodilator"),
            ("Asthalin", "Salbutamol", "Bronchodilator"),
            ("Ventolin", "Salbutamol", "Bronchodilator"),
            ("Budecort", "Budesonide", "Inhaled Corticosteroid"),
            ("Pulmicort", "Budesonide", "Inhaled Corticosteroid"),
            ("Foracort", "Formoterol + Budesonide", "LABA + ICS"),
            ("Seroflo", "Salmeterol + Fluticasone", "LABA + ICS"),
            ("Symbicort", "Formoterol + Budesonide", "LABA + ICS"),
            ("Tiova", "Tiotropium", "LAMA"),
            ("Spiriva", "Tiotropium", "LAMA"),
            ("Duolin", "Ipratropium + Levosalbutamol", "Bronchodilator Combination"),
            ("Montelukast", "Montelukast", "Leukotriene Antagonist"),
            ("Montair", "Montelukast", "Leukotriene Antagonist"),
            ("Singulair", "Montelukast", "Leukotriene Antagonist"),
            ("Alex", "Phenylephrine + Chlorpheniramine + Dextromethorphan", "Cough Suppressant"),
            ("Benadryl", "Diphenhydramine", "Antihistamine"),
            ("Allegra", "Fexofenadine", "Antihistamine"),
            ("Cetirizine", "Cetirizine", "Antihistamine"),
            ("Levocet", "Levocetirizine", "Antihistamine"),
            ("Xyzal", "Levocetirizine", "Antihistamine"),
            ("Sinarest", "Paracetamol + Phenylephrine + Chlorpheniramine", "Decongestant Combination"),
            ("Mucinex", "Guaifenesin", "Expectorant"),
            ("Ambrolite", "Ambroxol", "Mucolytic"),
            ("Mucomix", "Acetylcysteine", "Mucolytic"),

            # --- Steroids ---
            ("Wysolone", "Prednisolone", "Corticosteroid"),
            ("Omnacortil", "Prednisolone", "Corticosteroid"),
            ("Prednisolone", "Prednisolone", "Corticosteroid"),
            ("Medrol", "Methylprednisolone", "Corticosteroid"),
            ("Deflazacort", "Deflazacort", "Corticosteroid"),
            ("Defcort", "Deflazacort", "Corticosteroid"),
            ("Dexamethasone", "Dexamethasone", "Corticosteroid"),
            ("Decadron", "Dexamethasone", "Corticosteroid"),
            ("Hydrocortisone", "Hydrocortisone", "Corticosteroid"),

            # --- Supplements ---
            ("Shelcal", "Calcium + Vitamin D3", "Calcium Supplement"),
            ("Calcimax", "Calcium + Vitamin D3", "Calcium Supplement"),
            ("CCM", "Calcium + Vitamin D3", "Calcium Supplement"),
            ("Gemcal", "Calcium Carbonate + Calcitriol", "Calcium Supplement"),
            ("Tayo", "Cholecalciferol", "Vitamin D Supplement"),
            ("D3 Must", "Cholecalciferol", "Vitamin D Supplement"),
            ("Uprise D3", "Cholecalciferol", "Vitamin D Supplement"),
            ("Calcirol", "Cholecalciferol", "Vitamin D Supplement"),
            ("Folvite", "Folic Acid", "Vitamin Supplement"),
            ("Neurobion", "Vitamin B Complex", "Vitamin Supplement"),
            ("Methylcobalamin", "Methylcobalamin", "Vitamin B12 Supplement"),
            ("Mecobalamin", "Methylcobalamin", "Vitamin B12 Supplement"),
            ("Mecobion", "Methylcobalamin", "Vitamin B12 Supplement"),
            ("Methycobal", "Methylcobalamin", "Vitamin B12 Supplement"),
            ("Orofer-XT", "Iron + Folic Acid", "Iron Supplement"),
            ("Autrin", "Iron + Folic Acid", "Iron Supplement"),
            ("Livogen", "Iron + Folic Acid", "Iron Supplement"),
            ("Ferrous Sulfate", "Ferrous Sulfate", "Iron Supplement"),
            ("Potklor", "Potassium Chloride", "Potassium Supplement"),
            ("Zinc", "Zinc", "Mineral Supplement"),
            ("Zincovit", "Multivitamin with Zinc", "Multivitamin"),
            ("Becosules", "B-Complex + Vitamin C", "Vitamin Supplement"),
            ("Revital", "Multivitamin", "Multivitamin"),

            # --- Neuro / Psych ---
            ("Eptoin", "Phenytoin", "Antiepileptic"),
            ("Dilantin", "Phenytoin", "Antiepileptic"),
            ("Levipil", "Levetiracetam", "Antiepileptic"),
            ("Keppra", "Levetiracetam", "Antiepileptic"),
            ("Levera", "Levetiracetam", "Antiepileptic"),
            ("Valproate", "Sodium Valproate", "Antiepileptic"),
            ("Valparin", "Sodium Valproate", "Antiepileptic"),
            ("Encorate", "Sodium Valproate", "Antiepileptic"),
            ("Carbamazepine", "Carbamazepine", "Antiepileptic"),
            ("Tegretol", "Carbamazepine", "Antiepileptic"),
            ("Zen", "Carbamazepine", "Antiepileptic"),
            ("Oxetol", "Oxcarbazepine", "Antiepileptic"),
            ("Trileptal", "Oxcarbazepine", "Antiepileptic"),
            ("Clobazam", "Clobazam", "Benzodiazepine"),
            ("Frisium", "Clobazam", "Benzodiazepine"),
            ("Clonazepam", "Clonazepam", "Benzodiazepine"),
            ("Petril", "Clonazepam", "Benzodiazepine"),
            ("Restyl", "Alprazolam", "Benzodiazepine"),
            ("Alprax", "Alprazolam", "Benzodiazepine"),
            ("Nexito", "Escitalopram", "SSRI"),
            ("Cipralex", "Escitalopram", "SSRI"),
            ("Fluoxetine", "Fluoxetine", "SSRI"),
            ("Fludac", "Fluoxetine", "SSRI"),
            ("Sertraline", "Sertraline", "SSRI"),
            ("Daxid", "Sertraline", "SSRI"),
            ("Amitriptyline", "Amitriptyline", "Tricyclic Antidepressant"),
            ("Tryptomer", "Amitriptyline", "Tricyclic Antidepressant"),
            ("Olanzapine", "Olanzapine", "Antipsychotic"),
            ("Oleanz", "Olanzapine", "Antipsychotic"),
            ("Risperidone", "Risperidone", "Antipsychotic"),
            ("Risperdal", "Risperidone", "Antipsychotic"),
            ("Sizodon", "Risperidone", "Antipsychotic"),
            ("Quetiapine", "Quetiapine", "Antipsychotic"),
            ("Qutan", "Quetiapine", "Antipsychotic"),
            ("Donepezil", "Donepezil", "Cholinesterase Inhibitor"),
            ("Aricept", "Donepezil", "Cholinesterase Inhibitor"),

            # --- Thyroid ---
            ("Thyronorm", "Levothyroxine", "Thyroid Hormone"),
            ("Eltroxin", "Levothyroxine", "Thyroid Hormone"),
            ("Thyrox", "Levothyroxine", "Thyroid Hormone"),
            ("Neomercazole", "Carbimazole", "Anti-thyroid"),

            # --- Miscellaneous ---
            ("Febuxostat", "Febuxostat", "Uric Acid Lowering"),
            ("Febuget", "Febuxostat", "Uric Acid Lowering"),
            ("Allopurinol", "Allopurinol", "Uric Acid Lowering"),
            ("Zyloric", "Allopurinol", "Uric Acid Lowering"),
            ("Colchicine", "Colchicine", "Anti-gout"),
            ("Hydroxychloroquine", "Hydroxychloroquine", "DMARD"),
            ("HCQS", "Hydroxychloroquine", "DMARD"),
            ("Methotrexate", "Methotrexate", "DMARD"),
            ("Folitrax", "Methotrexate", "DMARD"),
            ("Cyclophosphamide", "Cyclophosphamide", "Immunosuppressant"),
            ("Mycophenolate", "Mycophenolate Mofetil", "Immunosuppressant"),
            ("Tacrolimus", "Tacrolimus", "Immunosuppressant"),
            ("Pangraf", "Tacrolimus", "Immunosuppressant"),
            ("Sildenafil", "Sildenafil", "PDE5 Inhibitor"),
            ("Tamsulosin", "Tamsulosin", "Alpha Blocker"),
            ("Urimax", "Tamsulosin", "Alpha Blocker"),
            ("Finasteride", "Finasteride", "5-alpha Reductase Inhibitor"),
            ("Finpecia", "Finasteride", "5-alpha Reductase Inhibitor"),
            ("Mannitol", "Mannitol", "Osmotic Diuretic"),
            ("Heparin", "Heparin", "Anticoagulant"),
            ("Phenytoin", "Phenytoin", "Antiepileptic"),
            ("Ondansetron", "Ondansetron", "Antiemetic"),
            ("Ivabradine", "Ivabradine", "Heart Rate Lowering"),
            ("Procoralan", "Ivabradine", "Heart Rate Lowering"),
            ("Sacubitril", "Sacubitril + Valsartan", "ARNI"),
            ("Entresto", "Sacubitril + Valsartan", "ARNI"),
            ("Vymada", "Sacubitril + Valsartan", "ARNI"),
        ]

        for brand, generic, category in builtin:
            key = brand.upper()
            self._brand_map[key] = {"generic": generic, "category": category}
            self._generic_map[generic.upper()] = category
            self._all_names.add(key)
            self._all_names.add(generic.upper())

    # ------------------------------------------------------------------
    # CSV loading
    # ------------------------------------------------------------------

    def load_reference(self, path: str) -> None:
        """Load drug reference data from a CSV file.

        Expected columns (case-insensitive): ``brand_name``,
        ``generic_name``, ``category``.
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.warning("Drug reference file not found: %s – using built-in reference only.", path)
            return

        rows_loaded = 0
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(file_path, encoding=encoding, newline="") as fh:
                    reader = csv.DictReader(fh)
                    if reader.fieldnames is None:
                        logger.warning("Empty CSV: %s", path)
                        return

                    col_map: dict[str, str] = {}
                    for fn in reader.fieldnames:
                        col_map[fn.strip().lower().replace(" ", "_")] = fn

                    generic_col = col_map.get("generic_name") or col_map.get("generic")
                    brand_col = (
                        col_map.get("common_brands")
                        or col_map.get("brand_name")
                        or col_map.get("brands")
                        or col_map.get("brand")
                    )
                    cat_col = (
                        col_map.get("drug_class")
                        or col_map.get("category")
                        or col_map.get("drug_category")
                        or col_map.get("class")
                    )
                    purpose_col = (
                        col_map.get("plain_language_purpose")
                        or col_map.get("purpose")
                        or col_map.get("plain_language")
                    )
                    dose_forms_col = col_map.get("dose_forms") or col_map.get("form") or col_map.get("forms")
                    strengths_col = col_map.get("typical_strengths") or col_map.get("strengths") or col_map.get("strength")
                    aka_col = col_map.get("also_known_as") or col_map.get("aliases") or col_map.get("synonyms")
                    discharge_col = col_map.get("used_at_discharge")

                    if not generic_col or (not brand_col and not cat_col):
                        logger.warning("CSV %s missing required drug columns. Found: %s",
                                       path, reader.fieldnames)
                        return

                    for row in reader:
                        generic = (row.get(generic_col) or "").strip()
                        if not generic:
                            continue

                        category = (row.get(cat_col) or "").strip() if cat_col else ""
                        purpose = (row.get(purpose_col) or "").strip() if purpose_col else ""
                        dose_forms = (row.get(dose_forms_col) or "").strip() if dose_forms_col else ""
                        strengths = (row.get(strengths_col) or "").strip() if strengths_col else ""
                        discharge = (row.get(discharge_col) or "").strip() if discharge_col else ""
                        raw_brands = (row.get(brand_col) or "").strip() if brand_col else ""
                        raw_aka = (row.get(aka_col) or "").strip() if aka_col else ""

                        # Semicolon-separated brands in official organizer dataset
                        brands = [b.strip() for b in raw_brands.split(";") if b.strip()]
                        aliases = [a.strip() for a in raw_aka.split(";") if a.strip()]

                        if raw_brands and not brands:
                            brands = [raw_brands]

                        gen_key = generic.upper()
                        self._generic_map[gen_key] = category
                        self._all_names.add(gen_key)

                        if " + " in generic:
                            for comp in generic.split(" + "):
                                comp_key = comp.strip().upper()
                                if comp_key:
                                    self._all_names.add(comp_key)

                        detail = {
                            "generic_name": generic,
                            "category": category,
                            "drug_class": category,
                            "plain_language_purpose": purpose,
                            "dose_forms": dose_forms,
                            "typical_strengths": strengths,
                            "common_brands": brands,
                            "also_known_as": aliases,
                            "used_at_discharge": discharge,
                        }
                        self._drug_details[gen_key] = detail

                        # Map each brand name
                        for b in brands:
                            b_key = b.upper()
                            self._brand_map[b_key] = {
                                "generic": generic,
                                "category": category,
                                "purpose": purpose,
                                "dose_forms": dose_forms,
                                "strengths": strengths,
                            }
                            self._all_names.add(b_key)

                        # Map each alias / synonym
                        for a in aliases:
                            a_key = a.upper()
                            self._brand_map[a_key] = {
                                "generic": generic,
                                "category": category,
                                "purpose": purpose,
                                "dose_forms": dose_forms,
                                "strengths": strengths,
                            }
                            self._all_names.add(a_key)

                        rows_loaded += 1

                logger.info("Loaded %d drug mappings from %s", rows_loaded, path)
                return
            except UnicodeDecodeError:
                continue
            except Exception:
                logger.exception("Error reading drug reference %s", path)
                return

        logger.warning("Could not decode drug reference file %s with any supported encoding.", path)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_generic_name(self, brand_name: str) -> Optional[str]:
        """Return the generic name for a brand, or ``None``.

        Case-insensitive lookup.
        """
        if not brand_name:
            return None
        entry = self._brand_map.get(brand_name.strip().upper())
        if entry:
            return entry["generic"]
        # Maybe the caller passed a generic name directly
        if brand_name.strip().upper() in self._generic_map:
            return brand_name.strip()
        return None

    def get_category(self, medicine_name: str) -> Optional[str]:
        """Return the drug category for either a brand or generic name."""
        if not medicine_name:
            return None
        key = medicine_name.strip().upper()
        entry = self._brand_map.get(key)
        if entry and entry["category"]:
            return entry["category"]
        cat = self._generic_map.get(key)
        if cat:
            return cat
        return None

    def get_purpose(self, medicine_name: str) -> Optional[str]:
        """Return the plain-language purpose for a brand or generic name."""
        if not medicine_name:
            return None
        key = medicine_name.strip().upper()
        entry = self._brand_map.get(key)
        if entry and entry.get("purpose"):
            return entry["purpose"]
        detail = self._drug_details.get(key)
        if detail and detail.get("plain_language_purpose"):
            return detail["plain_language_purpose"]
        return None

    def get_dose_forms(self, medicine_name: str) -> Optional[str]:
        """Return typical dose forms for a brand or generic name."""
        if not medicine_name:
            return None
        key = medicine_name.strip().upper()
        entry = self._brand_map.get(key)
        if entry and entry.get("dose_forms"):
            return entry["dose_forms"]
        detail = self._drug_details.get(key)
        if detail and detail.get("dose_forms"):
            return detail["dose_forms"]
        return None

    def get_typical_strengths(self, medicine_name: str) -> Optional[str]:
        """Return typical strengths for a brand or generic name."""
        if not medicine_name:
            return None
        key = medicine_name.strip().upper()
        entry = self._brand_map.get(key)
        if entry and entry.get("strengths"):
            return entry["strengths"]
        detail = self._drug_details.get(key)
        if detail and detail.get("typical_strengths"):
            return detail["typical_strengths"]
        return None

    def get_drug_details(self, medicine_name: str) -> Optional[dict[str, Any]]:
        """Return complete drug record dict for a brand or generic name."""
        if not medicine_name:
            return None
        key = medicine_name.strip().upper()
        # Direct generic match
        if key in self._drug_details:
            return self._drug_details[key]
        # Brand match -> lookup generic
        entry = self._brand_map.get(key)
        if entry:
            gen_key = entry["generic"].upper()
            return self._drug_details.get(gen_key, entry)
        return None

    def is_known_medicine(self, name: str) -> bool:
        """Return ``True`` if *name* matches any brand or generic entry."""
        if not name:
            return False
        return name.strip().upper() in self._all_names

    def search(self, query: str) -> list[dict[str, str]]:
        """Return all entries whose brand or generic name contains *query*.

        Useful for fuzzy / partial lookups.  Returns list of dicts with
        keys ``brand``, ``generic``, ``category``.
        """
        if not query:
            return []
        q = query.strip().upper()
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for brand_upper, info in self._brand_map.items():
            if q in brand_upper or q in info["generic"].upper():
                dup_key = f"{brand_upper}|{info['generic'].upper()}"
                if dup_key not in seen:
                    seen.add(dup_key)
                    results.append({
                        "brand": brand_upper.title() if brand_upper == brand_upper else brand_upper,
                        "generic": info["generic"],
                        "category": info["category"],
                    })
        return results

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    @property
    def total_entries(self) -> int:
        """Number of brand → generic mappings loaded."""
        return len(self._brand_map)

    def __repr__(self) -> str:
        return f"<MedicineMapper entries={self.total_entries}>"

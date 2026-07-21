from extraction.base_extractor import BaseExtractor
from extraction.cin_extractor import CINExtractor
from extraction.acte_naissance_extractor import ActeNaissanceExtractor
from extraction.bac_extractor import BacExtractor
from extraction.licence_extractor import LicenceExtractor
from extraction.releve_extractor import ReleveExtractor

EXTRACTORS = {
    "cin": CINExtractor(),
    "acte_naissance": ActeNaissanceExtractor(),
    "bac": BacExtractor(),
    "diplome_licence": LicenceExtractor(),
    "releve_notes": ReleveExtractor(),
}


def get_extractor(document_type: str) -> BaseExtractor | None:
    return EXTRACTORS.get(document_type)

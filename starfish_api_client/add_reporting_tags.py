from starfish_api_client import StarfishAPIClient


class StarfishTagger:
    def __init__(self, sf: StarfishAPIClient):
        self.sf = sf

    def add_reporting_tags(self, tag: str, results: list, fn_attr: str = 'fn', blacklist: list = ()) -> None:
        filenames = StarfishTagger.get_untagged_filenames(results, fn_attr)
        filenames = StarfishTagger.filter_filenames(filenames, blacklist)
        for f in filenames:
            self.sf.add_tag(f"{tag}:{f}", f"Reporting:{f}")

    @staticmethod
    def get_untagged_filenames(results: list, attribute: str) -> list:
        return [r[attribute] for r in results if 'Reporting:' not in r['tags_explicit']]

    @staticmethod
    def filter_filenames(filenames: list, blacklist: list):
        return [f for f in filenames if (f.startswith('.') or f.startswith('systemd') or f == 'mmfs' or f in blacklist)]

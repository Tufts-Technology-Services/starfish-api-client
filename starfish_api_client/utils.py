
def get_most_recent_scans(scans):
    """
    Narrow scan data to the most recent and last successful scan for each volume.
    :param volumes: list of volumes to query
    :return: list of recent scan data
    """
    scans_narrowed = []
    volumes = set(s['volume'] for s in scans['scans'])
    for volume in volumes:
        latest_time = max(
            s['creation_time'] for s in scans['scans']
            if s['volume'] == volume
        )
        latest_scan = next(
            s for s in scans['scans']
            if s['creation_time'] == latest_time and s['volume'] == volume
        )
        scans_narrowed.append(latest_scan)
        if latest_scan['state']['is_running'] or latest_scan['state']['is_successful']:
            last_completed_time = max(
                s['creation_time'] for s in scans['scans']
                if not s['state']['is_running']
                and s['state']['is_successful'] and s['volume'] == volume
            )
            last_completed = next(
                s for s in scans['scans']
                if s['creation_time'] == last_completed_time
                and s['volume'] == volume
            )
            scans_narrowed.append(last_completed)
    return scans_narrowed

def get_schedule(jobs):
    unique_jobs = {}
    for job in jobs:
        if job.key not in unique_jobs:
            unique_jobs[job.key] = job
    jobs = list(unique_jobs.values())

    added_to_schedule = []
    schedule = []
    while len(jobs) > 0:
        job_round = []
        for job in jobs:
            if len(job.stale_precursors) == 0:
                job_round.append(job)
            elif all([dependency in added_to_schedule for dependency in job.stale_dependencies]):
                job_round.append(job)

        for job in job_round:
            jobs.remove(job)
        added_to_schedule += job_round
        schedule.append(job_round)
    return schedule

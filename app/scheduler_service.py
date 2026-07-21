import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from threading import Event
from jobs import downloadFlyersJob

logger = logging.getLogger('tartine.scheduler')


def _job_listener(event):
    try:
        job_id = getattr(event, 'job_id', 'unknown')
        if event.exception:
            logger.error("Job %s a levé une exception: %s", job_id, event.exception)
        else:
            logger.info("Job %s exécutée avec succès", job_id)
    except Exception:
        logger.exception("Erreur dans le listener APScheduler")


def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        downloadFlyersJob,
        'cron',
        day_of_week='thu',
        hour=3,
        minute=0,
        timezone='America/Montreal',
        id='downloadFlyersJob'
    )
    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    scheduler.start()
    logger.info("Scheduler service started (job id: downloadFlyersJob)")

    # block forever
    Event().wait()


if __name__ == "__main__":
    main()

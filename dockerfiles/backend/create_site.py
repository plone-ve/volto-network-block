from AccessControl.SecurityManagement import newSecurityManager
from datetime import datetime
from pathlib import Path
from Products.CMFCore.exportimport.actions import importActionProviders
from Products.CMFPlone.factory import _DEFAULT_PROFILE
from Products.CMFPlone.factory import addPloneSite
from Products.GenericSetup.tests.common import DummyImportContext
from Testing.makerequest import makerequest
from zope.component.hooks import setSite


import transaction
import os


truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))


def asbool(s):
    """Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is a :term:`truthy string`. If ``s`` is already one of the
    boolean values ``True`` or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy


app = makerequest(app)

request = app.REQUEST

admin = app.acl_users.getUserById("admin")
admin = admin.__of__(app.acl_users)
newSecurityManager(None, admin)

# VARS
TYPE = os.getenv("TYPE", "volto")
SITE_ID = os.getenv("SITE_ID", "Plone")
SETUP_CONTENT = asbool(os.getenv("SETUP_CONTENT"))
DELETE_EXISTING = asbool(os.getenv("DELETE_EXISTING"))
LANGUAGE = os.getenv("LANGUAGE", "en")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")
ADDITIONAL_PROFILES = os.getenv("PROFILES", os.getenv("ADDITIONAL_PROFILES", ""))

PROFILES = {
    "volto": [
        "plone.app.caching:default",
        "plonetheme.barceloneta:default",
        "plone.volto:default",
        "plone.volto:default-homepage",
    ],
    "classic": [
        "plone.app.caching:default",
        "plonetheme.barceloneta:default",
    ],
}


def profile_ids(site_type):
    extension_ids = PROFILES[site_type]
    if ADDITIONAL_PROFILES:
        extension_ids.extend(
            [
                profile.strip()
                for profile in ADDITIONAL_PROFILES.split(" ")
                if profile.strip()
            ]
        )
    return extension_ids


payload = {
    "title": "Plone",
    "profile_id": _DEFAULT_PROFILE,
    "extension_ids": profile_ids(TYPE),
    "setup_content": SETUP_CONTENT,
    "default_language": LANGUAGE,
    "portal_timezone": TIMEZONE,
}

if SITE_ID in app.objectIds() and DELETE_EXISTING:
    app.manage_delObjects([SITE_ID])
    transaction.commit()
    app._p_jar.sync()


if SITE_ID not in app.objectIds():
    seed = f"{datetime.now()}"
    with transaction.manager as t:
        site = addPloneSite(app, SITE_ID, **payload)
        site = app[SITE_ID]
        setSite(site)
        # Import actions.xml
        data = Path("actions.xml").read_text()
        context = DummyImportContext(site, purge=False)
        context._files['actions.xml'] = data
        importActionProviders(context)
        site.title = f"{site.title} - {seed}"
        t.note("Created new site")
        with open(Path(f"{seed}.log"), "w") as fh:
            fh.write(site.title)
    app._p_jar.sync()

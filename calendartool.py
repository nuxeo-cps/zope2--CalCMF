# -*- coding: ISO-8859-15 -*-
# (C) Copyright 2005 Nuxeo SARL <http://nuxeo.com>
# Author: Lennart Regebro <regebro@nuxeo.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
# $Id: calendartool.py 34269 2006-03-10 11:22:50Z lregebro $
"""
  calendartool.py
"""
from zope.interface import implements
from zope.app import zapi
from zope.app.component.interfaces import ILocalUtility

from DateTime import DateTime
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.Permissions import manage_users
from AccessControl.PermissionRole import rolesForPermissionOn
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Persistence import PersistentMapping

from Products.ZCatalog.ZCatalog import ZCatalog
from Products.CMFCore.utils import UniqueObject, getToolByName
from Products.CMFCore.utils import _getAuthenticatedUser, _checkPermission
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.permissions import View, setDefaultRoles
from Products.CMFCore.permissions import AddPortalContent

import Products.CalCore # Force it's loading and pythonpath patching

from Products.CalZope.interfaces import IZopeAttendeeSource
from Products.CalZope.zopecal import StorageManager, Calendar, Attendee
from calcore.interfaces import IAttendeeSource

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("calendar")

# id for default personal calendars
CALENDAR_ID = 'calendar'

EVENT_LIST = ['invite', 'status_change', 'deleted', 'modify']

class CmfAttendeeSource(UniqueObject, SimpleItem):

    implements(IZopeAttendeeSource, ILocalUtility)

    meta_type = "CMF Attendee Source"
    id = 'attendee_source'

    def getAttendee(self, attendee_id):
        # Look up member
        prefix, id = attendee_id.split('!', 1)

        if prefix == 'INDIVIDUAL':
            members = getToolByName(self, 'portal_membership')
            try:
                member = members.getMemberById(id)
                # Use a get since the directory may be misconfigured:
                title = member.getProperty('fullname', None)
                if title is None:
                    title = id
            except KeyError:
                title = 'Non-existing attendee (%s)' % id
            type = prefix
        elif prefix == 'CALENDAR':
            calendar = self.unrestrictedTraverse(id, None)
            if calendar is None: # Most likely a calendar that has been deleted
                type = 'UNKNOWN'
                title = 'Non-existing attendee (%s)' % id
            else:
                # During upgrade, you sometimes find old calendars.
                # These do not have an _attendee_type. Default to
                # UNKNOWN.
                type = getattr(calendar, '_attendee_type', 'UNKNOWN')
                title = calendar.title_or_id()
        else:
            raise 'Unknown attendee prefix: %s' % prefix
        attendee = CmfAttendee(id, title, type)
        homecal = self.getMainCalendarForAttendeeId(attendee_id)
        if homecal is None:
            return attendee.__of__(self)
        # This is to acquire the security settings from the calendar:
        return attendee.__of__(homecal)


    def findByName(self, query_str, attendee_type=None):
        """Search for attendees"""
        if isinstance(query_str, unicode):
            query_str = query_str.encode('ISO-8859-15', 'ignore')
        
        if query_str == '': # Empty string means no match
            return []

        if query_str == '*': # Asterix means "everything"
            query_str  = ''

        catalog = getToolByName(self, 'portal_catalog')
        # XXX for workspace calendars (at least), we should be able to include 
        # the title in the search.
        search = catalog.unrestrictedSearchResults(meta_type='CalCMF Calendar')
        result = []
        attendee_ids = []
        for brain in search:
            ob = self.unrestrictedTraverse(brain.getPath(), None)
            if ob is None:
                # Object that was deleted but not unindexed, probably.
                # That shouldn't really happen, so I should have a debug log here.
                continue
            if not _checkPermission('Invite attendee', ob):
                # You can't invite this guy, so skip him.
                continue

            # Filter on attendee_type
            if (attendee_type is not None and
                getattr(ob, '_attendee_type', None) != attendee_type):
                continue

            attendee = ob.getMainAttendee()
            title = attendee.title
            if isinstance(title, unicode):
                title = title.encode('ISO-8859-15', 'ignore')
            if title.lower().find(query_str.lower()) == -1:
                continue
            
            attendee_id = attendee.getAttendeeId()
            if attendee_id in attendee_ids:
                continue
            # It's a match!
            attendee_ids.append(attendee_id)
            result.append(attendee)
        return result

    def getAttendeesOfType(self, attendee_type):
        return self.findByName(None, attendee_type)

    def getCurrentUserAttendee(self):
        securitymanager = getSecurityManager()
        id = securitymanager.getUser().getId()
        if not id:
            id = 'Anonymous'
        return self.getAttendee('INDIVIDUAL!' + id)

    def getAttendeeTypes(self):
        return ['INDIVIDUAL', 'WORKSPACE', 'RESOURCE']

    def getMainCalendarForAttendeeId(self, attendee_id):
        prefix, name = attendee_id.split('!', 1)
        if prefix == 'INDIVIDUAL':
            members = getToolByName(self, 'portal_membership')
            home = members.getHomeFolder(name)
            if CALENDAR_ID not in home.objectIds():
                return None
            return home.calendar
        
        try:
            return self.unrestrictedTraverse(name)
        except (KeyError, AttributeError):
            pass
        # The calendar may have moved, try to find it
        catalog = getToolByName(self, 'portal_catalog')
        search = catalog.searchResults(meta_type='CalCMF Calendar')
        for brain in search:
            ob = self.unrestrictedTraverse(brain.getPath(), None)
            # This search is for existing and non-individual calendars only.
            if ob is None or ob._attendee_type == 'INDIVIDUAL':
                continue
            if  ob._attendee_name == name:
                # Just return the first calendar that uses this id.
                return ob
        # Nope, none found.
        return None

    def getAttendeeFromSpec(self, vcaladdress):
        # MAILTO: and CUTYPE is not sufficient for CMF, rooms and
        # resources do not have any reasonable unique mail address.
        # For this reason, CalCMF put the type in CUTYPE and the
        # id in X-CID (experimental calendar id). We pick that up here
        # and look up the correct Attendee.

        id = vcaladdress.params.get('X-CID', None)
        if id is None:
            return None
        cutype = vcaladdress.params.get('CUTYPE', 'INDIVIDUAL')
        if cutype == 'INDIVIDUAL':
            prefix = cutype
        else:
            prefix = 'CALENDAR'
        if cutype == 'X-WORKSPACE':
            cutype = 'WORKSPACE'
        attendee = self.getAttendee('%s!%s' % (prefix, id))
        if (attendee._attendee_type == 'UNKNOWN' and
            cutype in self.getAttendeeTypes()):
            # Non-existing or non-upgraded attendees:
            attendee._attendee_type = cutype
        return attendee


    def getHomeCalendarObject(self, id=None, verifyPermission=0):
        """Return a member's home calendar object, or None."""
        mtool = getToolByName(self, 'portal_membership')
        if id is None:
            member = mtool.getAuthenticatedMember()
            if not hasattr(member, 'getMemberId'):
                return None

            id = member.getMemberId()

        member_home = mtool.getHomeFolder(id, verifyPermission)
        if member_home:
            try:
                calendar = member_home._getOb(CALENDAR_ID)
                if verifyPermission and not _checkPermission('View', calendar):
                    # Don't return the folder if the user can't get to it.
                    return None
                return calendar
            except AttributeError:
                pass
        return None

    def getHomeCalendarUrl(self, id=None, verifyPermission=0):
        """Return a member's home calendar url, or None."""
        calendar = self.getHomeCalendarObject(id, verifyPermission)
        if calendar is not None:
            return calendar.absolute_url()
        else:
            return None

    def createMemberCalendar(self, member_id=None, REQUEST=None):
        """Create a calendar in the home folder of a member

        member_id: member's id for which we create this calendar

        Precondition: member_id must be a valid user id
        """
        user = _getAuthenticatedUser(self)
        user_id = user.getUserName()
        if not member_id:
            member = user
            member_id = user_id
        elif user_id == member_id:
            member = user
        else:
            if _checkPermission(manage_users, 
                                self.portal_url.getPortalObject()):
                member = self.acl_users.getUserById(member_id, None)
                if member:
                    member = member.__of__(self.acl_users)
                else:
                    raise ValueError("Member %s does not exist" % member_id)
            else:
                raise 'Unauthorized', manage_users

        mtool = getToolByName(self, 'portal_membership')
        ttool = getToolByName(self, 'portal_types')

        context = mtool.getHomeFolder(member_id)
        if not context:
            raise ValueError, "Can not create calendar for members %s. "\
                  "Member has no home folder." % member_id

        # Check that the user has the permissions.
        if not _checkPermission(AddPortalContent, context):
            raise 'Unauthorized', AddPortalContent

        member = mtool.getMemberById(member_id)
        title = member.getProperty('fullname', None)
        
        # Can not import at top, it causes circular import problems
        from calendar import addCalCMFCalendar
        addCalCMFCalendar(context, CALENDAR_ID, title=title,
                          attendee_name=member_id, attendee_type='INDIVIDUAL')
        calendar = context._getOb(CALENDAR_ID)

        calendar_type_info = ttool.getTypeInfo('CalCMF Calendar')
        calendar_type_info._finishConstruction(calendar)

        # Grant ownership to Member (needed if it's created by a Manager, or so)
        calendar.changeOwnership(member)
        calendar.manage_setLocalRoles(member_id, ['Owner', 'WorkspaceManager', 'AttendeeManager'])

        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(
                '%s/%s' % (self.getHomeCalendarUrl(),
                           CALENDAR_ID))

        return calendar


class CmfAttendee(Attendee):
    """An attende with notifications"""

    def __init__(self, userid, title, attendee_type, on_invite=None):
        if attendee_type == 'INDIVIDUAL':
            prefix = 'INDIVIDUAL'
        else:
            prefix = 'CALENDAR'
        attendee_id = '!'.join([prefix, userid])
        Attendee.inheritedAttribute('__init__')(
            self, attendee_id, title, attendee_type, on_invite)
        self.id = attendee_id
        self.userid = userid
        self.title = title

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
# $Id: test_attendeesource.py 32789 2006-02-13 19:56:00Z lregebro $

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest, transaction
from datetime import datetime, timedelta

from zope.app import zapi

from calcore import cal
from calcore.interfaces import IStorageManager
from Products.CalZope.interfaces import IZopeAttendeeSource
from Products.CalCMF.calendar import CmfCalendar

from calendartest import CalendarTest

manager_id = 'manager'

class testAttendeSource(CalendarTest):
        
    def testRegisterAndLookup(self):
        # Create a calendar
        calendar = CmfCalendar('calendar', title='calendar')
        self.portal.workspaces._setObject('calendar', calendar)
        
        # This calendar should now have created an attendee:
        asrc = zapi.getUtility(IZopeAttendeeSource, context=self.portal)
        # This raises an error if not found, so an assert is not needed:
        attendee = asrc.getAttendee('CALENDAR!/portal/workspaces/calendar')
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')
        # Now, delete the calendar, and the attendee should be marked as gone:
        self.portal.workspaces._delObject('calendar')
        attendee = asrc.getAttendee('CALENDAR!/portal/workspaces/calendar')
        self.failUnless(attendee.getAttendeeType(), 'UNKNOWN')

    def testWorkspaceCalendarCopyPaste(self):
        asrc = zapi.getUtility(IZopeAttendeeSource, context=self.portal)
        ws = self.portal.workspaces

        calendar = CmfCalendar('calendar', title='calendar')
        ws._setObject('calendar', calendar)
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')

        # A copy of a workspace calendar should not create a new attendee
        cp = ws.manage_copyObjects('calendar')
        ws.manage_pasteObjects(cp)
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')

        # When the original calendar stil exists, finding the main calendar
        # is no problem:
        id = attendees[0].getAttendeeId()
        cal = asrc.getMainCalendarForAttendeeId(id)
        self.failIfEqual(cal, None)
        
        # If we delete the original calendar, the copy should become the new
        # main calendar (because the attendee source makes a search):
        self.portal.workspaces._delObject('calendar')
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')
        id = attendees[0].getAttendeeId()
        cal = asrc.getMainCalendarForAttendeeId(id)
        self.failIfEqual(cal, None)
        self.portal.workspaces._delObject('copy_of_calendar')
        transaction.commit()

    def testWorkspaceCalendarCutAndPaste(self):
        asrc = zapi.getUtility(IZopeAttendeeSource, context=self.portal)
        ws = self.portal.workspaces

        calendar = CmfCalendar('calendar', title='calendar')
        ws._setObject('calendar', calendar)
        transaction.commit() # Can't cut or move unless it's committed.
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')

        # A copy of a workspace calendar should not create a new attendee
        cp = ws.manage_cutObjects('calendar')
        ws.manage_pasteObjects(cp)
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')
        id = attendees[0].getAttendeeId()
        cal = asrc.getMainCalendarForAttendeeId(id)
        self.failIfEqual(cal, None)
        self.portal.workspaces._delObject('calendar')
        transaction.commit()
        
    def testWorkspaceCalendarRename(self):
        asrc = zapi.getUtility(IZopeAttendeeSource, context=self.portal)
        ws = self.portal.workspaces

        calendar = CmfCalendar('calendar', title='calendar')
        
        ws._setObject('calendar', calendar)
        transaction.commit() # Can't cut or move unless it's committed.
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')
        
        ws.manage_renameObject('calendar', 'new_calendar')
        attendees = asrc.findByName('calendar')
        self.failUnlessEqual(len(attendees), 1, 
                             'One and only one attendee was expected')
        id = attendees[0].getAttendeeId()
        cal = asrc.getMainCalendarForAttendeeId(id)
        self.failIfEqual(cal, None)
        self.portal.workspaces._delObject('new_calendar')


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(testAttendeSource),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')    

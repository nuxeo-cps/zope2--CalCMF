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
# $Id: calendartest.py 34008 2006-03-06 09:41:36Z lregebro $

from zope.app import zapi
import transaction

from AccessControl.SecurityManagement import newSecurityManager

from Testing.ZopeTestCase import user_name as user_id, installProduct
from Testing.ZopeTestCase.PortalTestCase import PortalTestCase, portal_name

from Products.CMFDefault.Portal import manage_addCMFSite
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from Products.CMFCore.PortalFolder import manage_addPortalFolder

from Products.CalZope.interfaces import IZopeAttendeeSource

installProduct('CMFCore')
installProduct('CMFDefault')
installProduct('MailHost')
installProduct('ZCTextIndex')
installProduct('CalZope')
installProduct('CalCMF')
installProduct('CMFonFive')
installProduct('Five')

manager_id = 'manager'

class CalendarTest(PortalTestCase):

    def getPortal(self):
        # Create a CMF portal
        if getattr(self.app, 'portal', None) is not None:
            return self.app.portal
        
        manage_addCMFSite(self.app, 'portal')
        # Install the calendar
        manage_addExternalMethod(self.app.portal, 'install_calendar', 
                                 'Install Calendar', 'CalCMF.install', 
                                 'install')
        self.app.portal.install_calendar()
        
        # Create a common folder.
        manage_addPortalFolder(self.app.portal, 'workspaces')

        # Set up users
        aclu = self.app.portal.acl_users
        if aclu.getUser(user_id) is None:
            aclu._doAddUser(user_id, '', [], [])
        if aclu.getUser(manager_id) is None:
            aclu._doAddUser(manager_id, '', ['Manager'], [])
        user = aclu.getUserById(manager_id)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(aclu)
        newSecurityManager(None, user)
        
        # Create home calendars
        asrc = zapi.getUtility(IZopeAttendeeSource, context=self.app.portal)
        mtool = self.app.portal.portal_membership
        mtool.createMemberArea(user_id)
        asrc.createMemberCalendar(user_id)
        mtool.createMemberArea(manager_id)
        asrc.createMemberCalendar(manager_id)
        return self.app.portal

    def afterSetUp(self):
        self.login(manager_id)

    def beforeTearDown(self):
        # Clear the workspaces folder from old calendars
        for id in self.portal.workspaces.objectIds():
            if id[0] != '.':
                self.portal.workspaces._delObject(id)
        transaction.commit()
        

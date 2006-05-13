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
# $Id: install.py 30261 2005-12-04 14:03:51Z lregebro $

from zope.app.site.interfaces import ISite
from zope.app import zapi

from AccessControl import getSecurityManager
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod

import Products.Five
from Products.Five import zcml
from Products.Five.site.interfaces import IFiveUtilityService
from Products.Five.site.localsite import enableLocalSiteHook
from Products.Five.site.tests.dummy import manage_addDummySite

from calcore.interfaces import IAttendeeSource, IStorageManager
from Products.CalZope.permissions import permissions as cal_permissions
from Products.CalZope.interfaces import IZopeAttendeeSource

from Products.CalZope.zopecal import StorageManager
from Products.CalCMF.calendartool import CmfAttendeeSource


def install(self):
    if not ISite.providedBy(self):
        enableLocalSiteHook(self)

    # Create tools
    try:
        sm = StorageManager()
        IFiveUtilityService(self).registerUtility(IStorageManager, sm)
    except ValueError:
        pass
    
    asrc = CmfAttendeeSource()
    try:
        IFiveUtilityService(self).registerUtility(IAttendeeSource, asrc)
    except ValueError:
        pass
    try:
        IFiveUtilityService(self).registerUtility(IZopeAttendeeSource, asrc)
    except ValueError:
        pass

    # Set up type:
    ttool = self.portal_types
    ttool.manage_addTypeInformation(
        id='CalCMF Calendar',
        add_meta_type='Factory-based Type Information',
        typeinfo_name='CalCMF: CalCMF Calendar (CalCMF Calendar)')
    
    # Set up standard permissions:
    from Products.CalZope.permissions import permissions
    for permission, roles in permissions.items():
        pms = self.rolesOfPermission(permission)
        p_roles = [r['name'] for r in pms if r['selected']]
        for role in roles:
            if role not in p_roles:
                p_roles.append(role)
        self.manage_permission(permission, p_roles, 1)

    # Add the Five action tool:
    if not 'portal_fiveactions' in self.objectIds():
        self.manage_addProduct['CMFonFive'].manage_addTool('Five Actions Tool')
        atool = self.portal_actions
        if not 'portal_fiveactions' in atool.listActionProviders():
            atool.addActionProvider('portal_fiveactions')

    # Install the personal calendar actions:
    atool = self.portal_actions
    all_actions = [action.id for action in atool.listActions()]
    if not 'my_calendar' in all_actions:
        atool.addAction(
            id='my_calendar',
            name='My calendar',
            action='string:${portal/utilities/IZopeAttendeeSource/getHomeCalendarUrl}',
            condition="portal/utilities/IZopeAttendeeSource/getHomeCalendarObject",
            permission=('View',),
            category='user',
            visible=1)

    if not 'create_my_calendar' in all_actions:
        atool.addAction(
            id='create_my_calendar',
            name='Create my home calendar',
            action='string:${portal_url}/utilities/IZopeAttendeeSource/createMemberCalendar',
            condition="python:portal.utilities.IZopeAttendeeSource.getHomeCalendarObject() is None",
            permission=('View',),
            category='user',
            visible=1)
        
    return "Install done!"


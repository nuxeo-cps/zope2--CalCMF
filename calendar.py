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
# $Id: calendar.py 32789 2006-02-13 19:56:00Z lregebro $

from zope.interface import implements
from zope.i18n import translate

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
from Products.CMFCore.PortalContent import PortalContent
from Products.CMFDefault.DublinCore import DefaultDublinCoreImpl

from Products.CalZope.zopecal import Calendar, EventList, WeekList, Year
from Products.Five.traversable import  FiveTraversable
from calendartool import CmfAttendee

factory_type_information = {
     'id': 'CalCMF Calendar',
     'title': 'A CalCMF Calendar',
     'description': 'An advanced calendar for CMF',
     'icon': '++resource++calcmf.png',
     'product': 'CalCMF',
     'meta_type': 'CalCMF Calendar',
     'factory': 'addCalCMFCalendar',
     'immediate_view': 'edit.html',
     'filter_content_types': 0,
     'allowed_content_types': (),
     'actions': ({'id': 'view',
                  'name': 'View',
                  'action': 'string:${object_url}/calendar.html',
                  'permissions': ('View',),
                  'visible': 0,
                  },)
     }

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("calcmf")

class CmfCalendar(CMFCatalogAware, Calendar, PortalContent, DefaultDublinCoreImpl):
    
    meta_type = 'CalCMF Calendar'
    description = ''
        
    def __init__(self, id, title='', attendee_name='', 
                 attendee_type='WORKSPACE'):
        Calendar.__init__(self, id, title)
        self._attendee_name = attendee_name
        self._attendee_type = attendee_type
        DefaultDublinCoreImpl.__init__(self, title=title)

    def getMainAttendee(self):
        caltool = self._getAttendeeSource()
        if self._attendee_type == 'INDIVIDUAL':
            return caltool.getAttendee('INDIVIDUAL!' + self._attendee_name)

        if self._attendee_name == '':
            # A calendar needs an attendee, and the attendee needs an id.
            # We'll just use the path to the place where it was first created
            # (which is not available during init, so we do it here).
            # TODO: There is a possibility of id conflicts this way, but we
            # worry about that later. 
            self._attendee_name = '/'.join(self.getPhysicalPath())
        attendee_id = '!'.join(('CALENDAR', self._attendee_name))
        return caltool.getAttendee(attendee_id)

    def getAttendees(self):
        return [self.getMainAttendee()] + Calendar.getAttendees(self)

    def title_or_id(self):
        # XXX This dies not seem to get properly translated....
        if self._attendee_type == 'INDIVIDUAL':
            dict = {'title': self.getMainAttendee().title.decode('ISO-8859-15')}
            message = _("Personal calendar for %(title)s")
        else:
            parent_title = self.aq_inner.aq_parent.title_or_id()
            if not isinstance(parent_title, unicode):
                parent_title = parent_title.decode('ISO-8859-15')
            dict = {'title': self.title.decode('ISO-8859-15'),
                    'parent': parent_title}
            if self._attendee_type == 'WORKSPACE':
                message = _("Workspace calendar %(title)s for %(parent)s")
            elif self._attendee_type == 'RESOURCE':
                message = _("Resource calendar %(title)s for %(parent)s")
            else:
                raise ValueError, "Unkown calendar type %s" % self._attendee_type
        
        title = translate(message, context=self.REQUEST)
        title = title % dict
        return title.encode('ISO-8859-15', 'xmlcharrefreplace')

    # CMF wants a Title method:
    Title = title_or_id
    

def addCalCMFCalendar(context, id, title='', attendee_name='', 
                          attendee_type='WORKSPACE', REQUEST=None):
    """Add a calendar."""
    obj = CmfCalendar(id, title, attendee_name, attendee_type)
    context._setObject(id, obj)
    if REQUEST is not None:
        REQUEST.response.redirect('edit.html')

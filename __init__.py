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
# $Id: __init__.py 34008 2006-03-06 09:41:36Z lregebro $

from Products.CMFCore.utils import ContentInit, ToolInit
from Products.CMFCore.permissions import AddPortalContent

import calendartool, calendar

def initialize(context):
    ContentInit('CalCMF Types',
                content_types = (calendar.CmfCalendar,),
                permission = AddPortalContent,
                extra_constructors = (calendar.addCalCMFCalendar,),
                fti = (calendar.factory_type_information,),
                ).initialize(context)

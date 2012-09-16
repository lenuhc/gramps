# -*- python -*-
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2011  Serge Noiraud
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

"""
Geography for one person and all his descendant
"""
#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gen.ggettext import gettext as _
import operator
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import time
import threading
from math import *

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger("GeoGraphy.geomoves")

#-------------------------------------------------------------------------
#
# Gramps Modules
#
#-------------------------------------------------------------------------
import gen.lib
from gen.config import config
import gen.datehandler
from gen.display.name import displayer as _nd
from gen.utils.place import conv_lat_lon
from gui.views.navigationview import NavigationView
from gui.views.bookmarks import PersonBookmarks
from maps import constants
from maps.geography import GeoGraphyView
from gui.selectors import SelectorFactory

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------

_UI_DEF = '''\
<ui>
<menubar name="MenuBar">
<menu action="GoMenu">
  <placeholder name="CommonGo">
    <menuitem action="Back"/>
    <menuitem action="Forward"/>
    <separator/>
    <menuitem action="HomePerson"/>
    <separator/>
  </placeholder>
</menu>
<menu action="BookMenu">
  <placeholder name="AddEditBook">
    <menuitem action="AddBook"/>
    <menuitem action="EditBook"/>
  </placeholder>
</menu>
</menubar>
<toolbar name="ToolBar">
<placeholder name="CommonNavigation">
  <toolitem action="Back"/>  
  <toolitem action="Forward"/>  
  <toolitem action="HomePerson"/>
</placeholder>
</toolbar>
</ui>
'''

#-------------------------------------------------------------------------
#
# GeoView : GeoMoves
#
#-------------------------------------------------------------------------
class GeoMoves(GeoGraphyView):
    """
    The view used to render all places visited by one person and all his descendants.
    """
    CONFIGSETTINGS = (
        ('geography.path', constants.GEOGRAPHY_PATH),

        ('geography.zoom', 10),
        ('geography.zoom_when_center', 12),
        ('geography.show_cross', True),
        ('geography.lock', True),
        ('geography.center-lat', 0.0),
        ('geography.center-lon', 0.0),

        ('geography.map_service', constants.OPENSTREETMAP),
        ('geography.max_places', 5000),

        # specific to geoclose :

        ('geography.color_base', 'orange'),
        ('geography.maximum_generations', 10),
        ('geography.generation_interval', 500),

        )

    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        GeoGraphyView.__init__(self, _("Descendance of the active person."),
                                      pdata, dbstate, uistate, 
                                      dbstate.db.get_bookmarks(), 
                                      PersonBookmarks,
                                      nav_group)
        self.dbstate = dbstate
        self.uistate = uistate
        self.place_list = []
        self.place_without_coordinates = []
        self.minlat = self.maxlat = self.minlon = self.maxlon = 0.0
        self.started = False
        self.minyear = 9999
        self.maxyear = 0
        self.nbplaces = 0
        self.nbmarkers = 0
        self.sort = []
        self.tracks = []
        self.additional_uis.append(self.additional_ui())
        self.skip_list = []
        self.track = []
        self.place_list_active = []
        self.place_list_ref = []
        self.cal = config.get('preferences.calendar-format-report')
        self.markers_by_level = dict()
        self.count = dict()
        self.no_show_places_in_status_bar = False

    def get_title(self):
        """
        Used to set the titlebar in the configuration window.
        """
        return _('GeoMoves')

    def get_stock(self):
        """
        Returns the name of the stock icon to use for the display.
        This assumes that this icon has already been registered 
        as a stock icon.
        """
        return 'geo-show-family'
    
    def get_viewtype_stock(self):
        """Type of view in category
        """
        return 'geo-show-family'

    def additional_ui(self):
        """
        Specifies the UIManager XML code that defines the menus and buttons
        associated with the interface.
        """
        return _UI_DEF

    def navigation_type(self):
        """
        Indicates the navigation type. Navigation type can be the string
        name of any of the primary objects.
        """
        return 'Person'

    def get_bookmarks(self):
        """
        Return the bookmark object
        """
        return self.dbstate.db.get_bookmarks()

    def goto_handle(self, handle=None):
        """
        Rebuild the tree with the given family handle as reference.
        """
        if not self.started:
            self.started = True
        self.place_list_active = []
        self.place_list_ref = []
        self.sort = []
        self.places_found = []
        self.place_without_coordinates = []
        self.remove_all_gps()
        self.remove_all_markers()
        self.lifeway_layer.clear_ways()
        self.date_layer.clear_dates()
        active = self.get_active()
        if active:
            p1 = self.dbstate.db.get_person_from_handle(active)
            self._createmap(p1)
        self.uistate.modify_statusbar(self.dbstate)

    def define_actions(self):
        """
        Define action for the reference family button.
        """
        NavigationView.define_actions(self)

    def build_tree(self):
        """
        This is called by the parent class when the view becomes visible. Since
        all handling of visibility is now in rebuild_trees, see that for more
        information.
        """
        self.place_list_active = []
        self.place_list_ref = []
        self.sort = []
        self.places_found = []
        self.place_without_coordinates = []
        self.remove_all_gps()
        self.remove_all_markers()
        self.lifeway_layer.clear_ways()
        self.date_layer.clear_dates()
        self.message_layer.clear_messages()

    def draw(self, menu, marks, color):
        """
        Create all displacements for one person's events.
        """
        points = []
        mark = None
        date = "    "
        for mark in marks:
            startlat = float(mark[3])
            startlon = float(mark[4])
            not_stored = True
            for idx in range(0, len(points)):
                if points[idx][0] == startlat and points[idx][1] == startlon:
                    not_stored = False
            if not_stored:
                points.append((startlat, startlon))
                if mark[6] is not None:
                    date = mark[6]
                if date != "    ":
                    self.date_layer.add_date(date[0:4])
        self.lifeway_layer.add_way(points, color)
        return False

    def _createmap_for_one_person(self, person, color):
        """
        Create all markers for each people's event in the database which has 
        a lat/lon.
        """
        self.place_list = []
        dbstate = self.dbstate
        if person is not None:
            # For each event, if we have a place, set a marker.
            for event_ref in person.get_event_ref_list():
                if not event_ref:
                    continue
                event = dbstate.db.get_event_from_handle(event_ref.ref)
                role = event_ref.get_role()
                try:
                    date = event.get_date_object().to_calendar(self.cal)
                except:
                    continue
                eyear = str("%04d" % date.get_year()) + \
                          str("%02d" % date.get_month()) + \
                          str("%02d" % date.get_day())
                place_handle = event.get_place_handle()
                if place_handle:
                    place = dbstate.db.get_place_from_handle(place_handle)
                    if place:
                        longitude = place.get_longitude()
                        latitude = place.get_latitude()
                        latitude, longitude = conv_lat_lon(latitude,
                                                           longitude, "D.D8")
                        descr = place.get_title()
                        evt = gen.lib.EventType(event.get_type())
                        descr1 = _("%(eventtype)s : %(name)s") % {
                                        'eventtype': evt,
                                        'name': _nd.display(person)}
                        # place.get_longitude and place.get_latitude return
                        # one string. We have coordinates when the two values
                        # contains non null string.
                        if ( longitude and latitude ):
                            self._append_to_places_list(descr, evt,
                                                        person.gramps_id, #_nd.display(person),
                                                        latitude, longitude,
                                                        descr1, eyear,
                                                        event.get_type(),
                                                        person.gramps_id,
                                                        place.gramps_id,
                                                        event.gramps_id,
                                                        role
                                                        )
                        else:
                            self._append_to_places_without_coord(
                                                        place.gramps_id, descr)
            family_list = person.get_family_handle_list()
            descr1 = " - "
            for family_hdl in family_list:
                family = self.dbstate.db.get_family_from_handle(family_hdl)
                if family is not None:
                    fhandle = family_list[0] # first is primary
                    fam = dbstate.db.get_family_from_handle(fhandle)
                    handle = fam.get_father_handle()
                    father = dbstate.db.get_person_from_handle(handle)
                    if father:
                        descr1 = "%s - " % _nd.display(father)
                    handle = fam.get_mother_handle()
                    mother = dbstate.db.get_person_from_handle(handle)
                    if mother:
                        descr1 = "%s%s" % ( descr1, _nd.display(mother))
                    for event_ref in family.get_event_ref_list():
                        if event_ref:
                            event = dbstate.db.get_event_from_handle(
                                            event_ref.ref)
                            role = event_ref.get_role()
                            if event.get_place_handle():
                                place_handle = event.get_place_handle()
                                if place_handle:
                                    place = dbstate.db.get_place_from_handle(
                                                    place_handle)
                                    if place:
                                        longitude = place.get_longitude()
                                        latitude = place.get_latitude()
                                        latitude, longitude = conv_lat_lon(
                                                  latitude, longitude, "D.D8")
                                        descr = place.get_title()
                                        evt = gen.lib.EventType(
                                                  event.get_type())
                                        eyear = str("%04d" % event.get_date_object().to_calendar(self.cal).get_year()) + \
                                                  str("%02d" % event.get_date_object().to_calendar(self.cal).get_month()) + \
                                                  str("%02d" % event.get_date_object().to_calendar(self.cal).get_day())
                                        if ( longitude and latitude ):
                                            self._append_to_places_list(descr, evt,
                                                 person.gramps_id, #_nd.display(person),
                                                 latitude, longitude,
                                                 descr1, eyear,
                                                 event.get_type(),
                                                 person.gramps_id,
                                                 place.gramps_id,
                                                 event.gramps_id,
                                                 role
                                                 )
                                        else:
                                            self._append_to_places_without_coord( place.gramps_id, descr)

            sort1 = sorted(self.place_list, key=operator.itemgetter(1,6))
            self.draw(None, sort1, color)
            # merge with the last results
            merge_list = self.sort
            for the_event in sort1 :
                if the_event not in merge_list:
                    merge_list.append(the_event)
            self.sort = sorted(merge_list, key=operator.itemgetter(6))

    def _add_person_to_list(self, person_id, level):
        """
        Create a list of uniq person.
        """
        if [person_id, level] not in self.person_list:
            self.person_list.append([person_id, level])
            try:
                self.count[level] += 1
            except:
                self.count[level] = 1

    def _prepare_for_one_family(self, family, level, curlevel):
        """
        Create all markers for one family : all event's places with a lat/lon.
        """
        dbstate = self.dbstate
        try:
            person = dbstate.db.get_person_from_handle(family.get_father_handle())
        except:
            return
        family_id = family.gramps_id
        if person is None: # family without father ?
            person = dbstate.db.get_person_from_handle(family.get_mother_handle())
        if person is None:
            person = dbstate.db.get_person_from_handle(self.uistate.get_active('Person'))
        if person is not None:
            self._add_person_to_list(person.gramps_id, curlevel-1)
            family_list = person.get_family_handle_list()
            for fhandle in family_list:
                fam = dbstate.db.get_family_from_handle(fhandle)
                handle = fam.get_father_handle()
                father = dbstate.db.get_person_from_handle(handle)
                if father:
                    self._createmap_for_next_level(father, level-1, level)
                    self._add_person_to_list(father.gramps_id, curlevel-1)
                handle = fam.get_mother_handle()
                mother = dbstate.db.get_person_from_handle(handle)
                if mother:
                    self._createmap_for_next_level(father, level-1, level)
                    self._add_person_to_list(mother.gramps_id, curlevel-1)
                index = 0
                child_ref_list = fam.get_child_ref_list()
                if child_ref_list:
                    for child_ref in child_ref_list:
                        child = dbstate.db.get_person_from_handle(child_ref.ref)
                        if child:
                            index += 1
                            self._createmap_for_next_level(child, level, curlevel)
                            self._add_person_to_list(child.gramps_id, curlevel)

    def _createmap_for_one_level(self, family, level, curlevel):
        """
        if maximum generation is not reached, show next level.
        """
        if level < curlevel:
            return
        self._prepare_for_one_family(family, level, curlevel+1)

    def _createmap_for_next_level(self, person, level, curlevel):
        """
        if maximum generation is not reached, show next level.
        """
        if level < curlevel:
            return
        try:
            if person not in self.markers_by_level[curlevel]:
                self.markers_by_level[curlevel].append(person)
        except:
            self.markers_by_level[curlevel] = []
            self.markers_by_level[curlevel].append(person)
        for family in person.get_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(family)
            self._createmap_for_one_level(fam, level, curlevel)
            if person not in self.markers_by_level[curlevel]:
                self.markers_by_level[curlevel].append(person)

    def _createmap(self, person):
        """
        Create all markers for each family's person in the database which has 
        a lat/lon.
        """
        dbstate = self.dbstate
        self.cal = config.get('preferences.calendar-format-report')
        self.place_list = []
        self.person_list = []
        self.count = dict()
        self.place_without_coordinates = []
        self.minlat = self.maxlat = self.minlon = self.maxlon = 0.0
        latitude = ""
        longitude = ""
        self.message_layer.clear_messages()
        self.place_without_coordinates = []
        self.minlat = self.maxlat = self.minlon = self.maxlon = 0.0
        if person is None:
            person = self.dbstate.db.get_person_from_handle(self.uistate.get_active('Person'))
            if not person:
                return
        self.message_layer.add_message(_("All descendance for %s" % _nd.display(person)))
        color = Gdk.color_parse(self._config.get('geography.color_base'))
        GObject.timeout_add(int(self._config.get("geography.generation_interval")),
                         self.animate_moves, 0, person, color)

    def animate_moves(self, index, person, color):
            """
            Animate all moves for one generation.
            """
            self.markers_by_level = dict()
            self._createmap_for_next_level(person, index, 0)
            try:
                persons = self.markers_by_level[index]
            except:
                return
            for people in persons:
                family_list = people.get_family_handle_list()
                for fhandle in family_list:
                    family = self.dbstate.db.get_family_from_handle(fhandle)
                    self._prepare_for_one_family(family, index, index+1)
            new_list = []
            for plx, level in self.person_list:
                plxp = self.dbstate.db.get_person_from_gramps_id(plx)
                birth = "0000"
                death = "0000"
                low_date = "9999" 
                high_date = "0000"
                for event_ref in plxp.get_event_ref_list():
                    if not event_ref:
                        continue
                    event = self.dbstate.db.get_event_from_handle(event_ref.ref)
                    role = event_ref.get_role()
                    try:
                        date = event.get_date_object().to_calendar(self.cal)
                        fyear = str("%04d" % date.get_year())
                        if event.get_type() == gen.lib.EventType.BIRTH:
                           birth = fyear
                        if event.get_type() == gen.lib.EventType.DEATH:
                           death = fyear
                        if fyear < low_date:
                            low_date = fyear
                        if fyear > high_date:
                            high_date = fyear

                    except:
                        pass
                    if birth == "0000":
                        birth = low_date
                    if death == "0000":
                        death = high_date
                new_list.append([level, plxp, birth, death])
            pidx = 0;
            if isinstance(color, str) :
                color = Gdk.color_parse(color)
            for (level, plxp, birth, death) in sorted(new_list, key=operator.itemgetter(0,2)):
                if index == int(self._config.get("geography.maximum_generations")):
                   break
                if level == index:
                    pidx += 1
                    self._createmap_for_one_person(plxp, color)
                    color.red = (float(color.red - (index)*3000)%65535)
                    if ( index % 2 ):
                        color.green = float((color.green + (index)*3000)%65535)
                    else:
                        color.blue = float((color.blue + (index)*3000)%65535)
                    self._createmap_for_one_person(person, color)
            if index < int(self._config.get("geography.maximum_generations")):
                time_to_wait = int(self._config.get("geography.generation_interval"))
                self._create_markers()
                # process next generation in a few milliseconds
                GObject.timeout_add(time_to_wait, self.animate_moves,
                                                  index+1, person, color)
            else:
                self.started = False
            return False

    def bubble_message(self, event, lat, lon, marks):
        """
        Create the menu for the selected marker
        """
        menu = Gtk.Menu()
        menu.set_title("descendance")
        events = []
        message = ""
        oldplace = ""
        prevmark = None
        # Be sure all markers are sorted by place then dates.
        for mark in sorted(marks, key=operator.itemgetter(0,6)):
            if mark[10] in events:
                continue # avoid duplicate events
            else:
                events.append(mark[10])
            if mark[0] != oldplace:
                message = "%s :" % mark[0]
                self.add_place_bubble_message(event, lat, lon,
                                              marks, menu,
                                              message, mark)
                oldplace = mark[0]
                message = ""
            evt = self.dbstate.db.get_event_from_gramps_id(mark[10])
            # format the date as described in preferences.
            date = gen.datehandler.displayer.display(evt.get_date_object())
            if date == "":
                date = _("Unknown")
            if ( mark[11] == gen.lib.EventRoleType.PRIMARY ):
                person = self.dbstate.db.get_person_from_gramps_id(mark[1])
                message = "(%s) %s : %s" % ( date, mark[2], _nd.display(person) )
            elif ( mark[11] == gen.lib.EventRoleType.FAMILY ):
                (father_name, mother_name) = self._get_father_and_mother_name(evt)
                message = "(%s) %s : %s - %s" % (date, mark[2],
                                                 father_name,
                                                 mother_name )
            else:
                descr = evt.get_description()
                if descr == "":
                    descr = _('No description')
                message = "(%s) %s => %s" % ( date, mark[11], descr)
            prevmark = mark
            add_item = Gtk.MenuItem(label=message)
            add_item.show()
            menu.append(add_item)
            itemoption = Gtk.Menu()
            itemoption.set_title(message)
            itemoption.show()
            add_item.set_submenu(itemoption)
            modify = Gtk.MenuItem(label=_("Edit Event"))
            modify.show()
            modify.connect("activate", self.edit_event,
                           event, lat, lon, prevmark)
            itemoption.append(modify)
            center = Gtk.MenuItem(label=_("Center on this place"))
            center.show()
            center.connect("activate", self.center_here,
                           event, lat, lon, prevmark)
            itemoption.append(center)
            menu.show()
            menu.popup(None, None,
                       lambda menu, data: (event.get_root_coords()[0],
                                           event.get_root_coords()[1], True),
                       None, event.button, event.time)
        return 1

    def add_specific_menu(self, menu, event, lat, lon): 
        """ 
        Add specific entry to the navigation menu.
        """ 
        return

    def get_default_gramplets(self):
        """
        Define the default gramplets for the sidebar and bottombar.
        """
        return (("Person Filter",),
                ())

    def specific_options(self, configdialog):
        """
        Add specific entry to the preference menu.
        Must be done in the associated view.
        """
        table = Gtk.Table(2, 2)
        table.set_border_width(12)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        configdialog.add_text(table,
                _('The maximum number of generations.\n'),
                1)
        self.max_generations = configdialog.add_slider(table, 
                "", 
                2, 'geography.maximum_generations',
                (1, 20))
        configdialog.add_text(table,
                _('Time in milliseconds between drawing two generations.\n'),
                3)
        self.max_generations = configdialog.add_slider(table, 
                "", 
                4, 'geography.generation_interval',
                (500, 3000))
        return _('The parameters for moves'), table

    def config_connect(self):
        """
        used to monitor changes in the ini file
        """
        self._config.connect('geography.maximum_generations',
                          self._maximum_generations)

    def _maximum_generations(self, client, cnxn_id, entry, data):
        """
        Called when the number of nomber of generations change
        """
        self.goto_handle(handle=None)

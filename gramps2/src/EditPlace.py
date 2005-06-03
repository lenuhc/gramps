#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2005  Donald N. Allingham
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

#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------
import cPickle as pickle
from gettext import gettext as _

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
import gobject
import gtk
import gtk.glade
import gnome

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
import const
import Utils
import Sources
import ImageSelect
import NameDisplay

from DdTargets import DdTargets


#-------------------------------------------------------------------------
#
# EditPlace
#
#-------------------------------------------------------------------------
class EditPlace:

    def __init__(self,parent,place,parent_window=None):
        self.parent = parent
        if place and place.get_handle():
            if self.parent.child_windows.has_key(place.get_handle()):
                self.parent.child_windows[place.get_handle()].present(None)
                return
            else:
                self.win_key = place.get_handle()
        else:
            self.win_key = self
        self.name_display = NameDisplay.displayer.display
        self.place = place
        self.db = parent.db
        self.child_windows = {}
        self.path = parent.db.get_save_path()
        self.not_loaded = 1
        self.lists_changed = 0
        if place:
            self.srcreflist = place.get_source_references()
            self.ref_not_loaded = 1
        else:
            self.srcreflist = []
            self.ref_not_loaded = 0

        self.top_window = gtk.glade.XML(const.placesFile,"placeEditor","gramps")
        self.top = self.top_window.get_widget("placeEditor")
        self.iconlist = self.top_window.get_widget('iconlist')
        title_label = self.top_window.get_widget('title')

        Utils.set_titles(self.top,title_label,_('Place Editor'))

        self.glry = ImageSelect.Gallery(place, self.db.commit_place, self.path,
                                        self.iconlist, self.db, self,self.top)

        mode = not self.parent.db.readonly
        self.title = self.top_window.get_widget("place_title")
        self.title.set_editable(mode)
        self.city = self.top_window.get_widget("city")
        self.city.set_editable(mode)
        self.parish = self.top_window.get_widget("parish")
        self.parish.set_editable(mode)
        self.county = self.top_window.get_widget("county")
        self.county.set_editable(mode)
        self.state = self.top_window.get_widget("state")
        self.state.set_editable(mode)
        self.phone = self.top_window.get_widget("phone")
        self.phone.set_editable(mode)
        self.postal = self.top_window.get_widget("postal")
        self.postal.set_editable(mode)
        self.country = self.top_window.get_widget("country")
        self.country.set_editable(mode)
        self.longitude = self.top_window.get_widget("longitude")
        self.longitude.set_editable(mode)
        self.latitude = self.top_window.get_widget("latitude")
        self.latitude.set_editable(mode)
        self.note = self.top_window.get_widget("place_note")
        self.note.set_editable(mode)

        self.web_list = self.top_window.get_widget("web_list")
        self.web_url = self.top_window.get_widget("web_url")
        self.web_go = self.top_window.get_widget("web_go")
        self.web_edit = self.top_window.get_widget("web_edit")
        self.web_description = self.top_window.get_widget("url_des")

        self.top_window.get_widget('changed').set_text(place.get_change_display())

        # event display
        self.web_model = gtk.ListStore(str,str)
        self.build_columns(self.web_list, [(_('Path'),150),
                                           (_('Description'),150)])
        self.web_list.set_model(self.web_model)
        self.web_list.get_selection().connect('changed',
                                              self.on_web_list_select_row)
        
        self.loc_edit = self.top_window.get_widget("loc_edit")
        self.loc_list = self.top_window.get_widget("loc_list")
        self.loc_city = self.top_window.get_widget("loc_city")
        self.loc_county = self.top_window.get_widget("loc_county")
        self.loc_state  = self.top_window.get_widget("loc_state")
        self.loc_postal = self.top_window.get_widget("loc_postal")
        self.loc_phone  = self.top_window.get_widget("loc_phone")
        self.loc_parish  = self.top_window.get_widget("loc_parish")
        self.loc_country = self.top_window.get_widget("loc_country")

        self.ulist = place.get_url_list()[:]
        self.llist = place.get_alternate_locations()[:]

        self.loc_model = gtk.ListStore(str,str,str,str)
        self.build_columns(self.loc_list, [(_('City'),150), (_('County'),100),
                                           (_('State'),100), (_('Country'),50)])
        self.loc_list.set_model(self.loc_model)
        self.loc_sel = self.loc_list.get_selection()
        self.loc_sel.connect('changed',self.on_loc_list_select_row)

        self.title.set_text(place.get_title())
        mloc = place.get_main_location()
        self.city.set_text(mloc.get_city())
        self.county.set_text(mloc.get_county())
        self.state.set_text(mloc.get_state())
        self.phone.set_text(mloc.get_phone())
        self.postal.set_text(mloc.get_postal_code())
        self.parish.set_text(mloc.get_parish())
        self.country.set_text(mloc.get_country())
        self.longitude.set_text(place.get_longitude())
        self.latitude.set_text(place.get_latitude())
        self.refinfo = self.top_window.get_widget("refinfo")
        self.slist = self.top_window.get_widget("slist")
        self.sources_label = self.top_window.get_widget("sourcesPlaceEdit")
        self.names_label = self.top_window.get_widget("namesPlaceEdit")
        self.notes_label = self.top_window.get_widget("notesPlaceEdit")
        self.gallery_label = self.top_window.get_widget("galleryPlaceEdit")
        self.inet_label = self.top_window.get_widget("inetPlaceEdit")
        self.refs_label = self.top_window.get_widget("refsPlaceEdit")
        self.flowed = self.top_window.get_widget("place_flowed")
        self.preform = self.top_window.get_widget("place_preform")

        self.note_buffer = self.note.get_buffer()
        if place.get_note():
            self.note_buffer.set_text(place.get_note())
            Utils.bold_label(self.notes_label)
            if place.get_note_format() == 1:
                self.preform.set_active(1)
            else:
                self.flowed.set_active(1)

        self.flowed.set_sensitive(mode)
        self.preform.set_sensitive(mode)

        if self.place.get_media_list():
            Utils.bold_label(self.gallery_label)

        self.top_window.signal_autoconnect({
            "on_switch_page"            : self.on_switch_page,
            "on_addphoto_clicked"       : self.glry.on_add_media_clicked,
            "on_selectphoto_clicked"    : self.glry.on_select_media_clicked,
            "on_deletephoto_clicked"    : self.glry.on_delete_media_clicked,
            "on_edit_photo_clicked"     : self.glry.on_edit_media_clicked,
            "on_edit_properties_clicked": self.glry.popup_change_description,
            "on_add_url_clicked"        : self.on_add_url_clicked,
            "on_delete_url_clicked"     : self.on_delete_url_clicked,
            "on_update_url_clicked"     : self.on_update_url_clicked,
            "on_add_loc_clicked"        : self.on_add_loc_clicked,
            "on_delete_loc_clicked"     : self.on_delete_loc_clicked,
            "on_update_loc_clicked"     : self.on_update_loc_clicked,
            "on_web_go_clicked"         : self.on_web_go_clicked,
            "on_help_clicked"           : self.on_help_clicked,
            "on_delete_event"           : self.on_delete_event,
            "on_cancel_clicked"         : self.close,
            "on_apply_clicked"          : self.on_place_apply_clicked,
            })

        self.sourcetab = Sources.SourceTab(
            self.srcreflist,self,
            self.top_window,self.top,self.slist,
            self.top_window.get_widget('add_src'),
            self.top_window.get_widget('edit_src'),
            self.top_window.get_widget('del_src'),
            self.parent.db.readonly)
        
        if self.place.get_handle() == None or self.parent.db.readonly:
            self.top_window.get_widget("add_photo").set_sensitive(0)
            self.top_window.get_widget("delete_photo").set_sensitive(0)

        self.web_list.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                    [DdTargets.URL.target()],
                                    gtk.gdk.ACTION_COPY)
        self.web_list.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [DdTargets.URL.target()],
                                      gtk.gdk.ACTION_COPY)
        self.web_list.connect('drag_data_get',
                              self.url_source_drag_data_get)
        self.web_list.connect('drag_data_received',
                              self.url_dest_drag_data_received)

        for name in ['del_name','add_name','sel_photo','add_url','del_url']:
            self.top_window.get_widget(name).set_sensitive(mode)

        self.redraw_url_list()
        self.redraw_location_list()
        if parent_window:
            self.top.set_transient_for(parent_window)
        self.add_itself_to_menu()
        self.top_window.get_widget('ok').set_sensitive(not self.db.readonly)
        self.top.show()
        if self.ref_not_loaded:
            Utils.temp_label(self.refs_label,self.top)
            gobject.idle_add(self.display_references)
            self.ref_not_loaded = 0

    def on_delete_event(self,obj,b):
        self.glry.close()
        self.close_child_windows()
        self.remove_itself_from_menu()

    def close(self,obj):
        self.glry.close()
        self.close_child_windows()
        self.remove_itself_from_menu()
        self.top.destroy()

    def close_child_windows(self):
        for child_window in self.child_windows.values():
            child_window.close(None)
        self.child_windows = {}

    def add_itself_to_menu(self):
        self.parent.child_windows[self.win_key] = self
        if not self.place.get_title():
            label = _("New Place")
        else:
            label = self.place.get_title()
        if not label.strip():
            label = _("New Place")
        label = "%s: %s" % (_('Place'),label)
        self.parent_menu_item = gtk.MenuItem(label)
        self.parent_menu_item.set_submenu(gtk.Menu())
        self.parent_menu_item.show()
        self.parent.winsmenu.append(self.parent_menu_item)
        self.winsmenu = self.parent_menu_item.get_submenu()
        self.menu_item = gtk.MenuItem(_('Place Editor'))
        self.menu_item.connect("activate",self.present)
        self.menu_item.show()
        self.winsmenu.append(self.menu_item)

    def remove_itself_from_menu(self):
        del self.parent.child_windows[self.win_key]
        self.menu_item.destroy()
        self.winsmenu.destroy()
        self.parent_menu_item.destroy()

    def present(self,obj):
        self.top.present()

    def on_help_clicked(self,obj):
        """Display the relevant portion of GRAMPS manual"""
        gnome.help_display('gramps-manual','adv-plc')

    def build_columns(self,tree,list):
        cnum = 0
        for name in list:
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name[0],renderer,text=cnum)
            column.set_min_width(name[1])
            cnum = cnum + 1
            tree.append_column(column)

    def url_dest_drag_data_received(self,widget,context,x,y,sel_data,info,time):
        if sel_data and sel_data.data:
            exec 'data = %s' % sel_data.data
            exec 'mytype = "%s"' % data[0]
            exec 'place = "%s"' % data[1]
            if place == self.place.get_handle() or mytype != 'url':
                return
            foo = pickle.loads(data[2]);
            self.ulist.append(foo)
            self.lists_changed = 1
            self.redraw_url_list()

    def url_source_drag_data_get(self,widget, context, sel_data, info, time):
        store,node = self.web_list.get_selection().get_selected()
        if not node:
            return
        row = store.get_path(node)
        url = self.ulist[row[0]]
        bits_per = 8; # we're going to pass a string
        pickled = pickle.dumps(url)
        data = str(('url',self.place.get_handle(),pickled))
        sel_data.set(sel_data.target, bits_per, data)

    def update_lists(self):
        self.place.set_url_list(self.ulist)
        self.place.set_alternate_locations(self.llist)
            
    def redraw_url_list(self):
        length = Utils.redraw_list(self.ulist,self.web_model,disp_url)
        if length > 0:
            self.web_go.set_sensitive(1)
            self.web_edit.set_sensitive(1)
            Utils.bold_label(self.inet_label)
        else:
            self.web_edit.set_sensitive(0)
            self.web_go.set_sensitive(0)
            self.web_url.set_text("")
            self.web_description.set_text("")
            Utils.unbold_label(self.inet_label)

    def redraw_location_list(self):
        Utils.redraw_list(self.llist,self.loc_model,disp_loc)
        if len(self.llist) > 0:
            self.loc_edit.set_sensitive(1)
            Utils.bold_label(self.names_label)
        else:
            self.loc_edit.set_sensitive(0)
            Utils.unbold_label(self.names_label)

    def on_web_go_clicked(self,obj):
        text = obj.get()
        if text != "":
            gnome.url_show(text)

    def set(self,field,getf,setf):
        text = unicode(field.get_text())
        if text != getf():
            setf(text)
    
    def on_place_apply_clicked(self,obj):

        note = unicode(self.note_buffer.get_text(self.note_buffer.get_start_iter(),
                                 self.note_buffer.get_end_iter(),False))
        format = self.preform.get_active()
        mloc = self.place.get_main_location()

        self.set(self.city,mloc.get_city,mloc.set_city)
        self.set(self.parish,mloc.get_parish,mloc.set_parish)
        self.set(self.state,mloc.get_state,mloc.set_state)
        self.set(self.phone,mloc.get_phone,mloc.set_phone)
        self.set(self.postal,mloc.get_postal_code,mloc.set_postal_code)
        self.set(self.county,mloc.get_county,mloc.set_county)
        self.set(self.country,mloc.get_country,mloc.set_country)
        self.set(self.title,self.place.get_title,self.place.set_title)
        self.set(self.longitude,self.place.get_longitude,
                 self.place.set_longitude)
        self.set(self.latitude,self.place.get_latitude,
                 self.place.set_latitude)

        if self.lists_changed:
            self.place.set_source_reference_list(self.srcreflist)
        
        if note != self.place.get_note():
            self.place.set_note(note)

        if format != self.place.get_note_format():
            self.place.set_note_format(format)

        self.update_lists()

        trans = self.db.transaction_begin()
        if self.place.get_handle():
            self.db.commit_place(self.place,trans)
        else:
            self.db.add_place(self.place,trans)
        self.db.transaction_commit(trans,
                                   _("Edit Place (%s)") % self.place.get_title())
        
        self.close(obj)

    def on_switch_page(self,obj,a,page):
        if page == 4 and self.not_loaded:
            self.not_loaded = 0
            self.glry.load_images()
        elif page == 6 and self.ref_not_loaded:
            self.ref_not_loaded = 0
            Utils.temp_label(self.refs_label,self.top)
            gobject.idle_add(self.display_references)
        text = unicode(self.note_buffer.get_text(self.note_buffer.get_start_iter(),
                                self.note_buffer.get_end_iter(),False))
        if text:
            Utils.bold_label(self.notes_label)
        else:
            Utils.unbold_label(self.notes_label)

    def on_update_url_clicked(self,obj):
        import UrlEdit
        store,node = self.web_list.get_selection().get_selected()
        if node:
            row = store.get_path(node)
            url = self.ulist[row[0]]
            name = ""
            if self.place:
            	name = self.place.get_title()
            UrlEdit.UrlEditor(self,name,url,self.url_edit_callback)

    def on_update_loc_clicked(self,obj):
        import LocEdit

        store,node = self.loc_sel.get_selected()
        if node:
            row = store.get_path(node)
            loc = self.llist[row[0]]
            LocEdit.LocationEditor(self,loc,self.top)

    def on_delete_url_clicked(self,obj):
        if Utils.delete_selected(obj,self.ulist):
            self.lists_changed = 1
            self.redraw_url_list()

    def on_delete_loc_clicked(self,obj):
        if Utils.delete_selected(obj,self.llist):
            self.lists_changed = 1
            self.redraw_location_list()

    def on_add_url_clicked(self,obj):
        import UrlEdit
        name = ""
        if self.place:
            name = self.place.get_title()
        UrlEdit.UrlEditor(self,name,None,self.url_edit_callback)

    def url_edit_callback(self,url):
        self.redraw_url_list()

    def on_add_loc_clicked(self,obj):
        import LocEdit
        LocEdit.LocationEditor(self,None,self.top)

    def on_web_list_select_row(self,obj):
        store,node = obj.get_selected()
        if not node:
            self.web_url.set_text("")
            self.web_go.set_sensitive(0)
            self.web_description.set_text("")
        else:
            row = store.get_path(node)
            url = self.ulist[row[0]]
            path = url.get_path()
            self.web_url.set_text(path)
            self.web_go.set_sensitive(1)
            self.web_description.set_text(url.get_description())

    def on_loc_list_select_row(self,obj):
        store,node = self.loc_sel.get_selected()
        if not node:
            self.loc_city.set_text('')
            self.loc_county.set_text('')
            self.loc_state.set_text('')
            self.loc_postal.set_text('')
            self.loc_phone.set_text('')
            self.loc_parish.set_text('')
            self.loc_country.set_text('')
        else:
            row = store.get_path(node)
            loc = self.llist[row[0]]

            self.loc_city.set_text(loc.get_city())
            self.loc_county.set_text(loc.get_county())
            self.loc_state.set_text(loc.get_state())
            self.loc_postal.set_text(loc.get_postal_code())
            self.loc_phone.set_text(loc.get_phone())
            self.loc_parish.set_text(loc.get_parish())
            self.loc_country.set_text(loc.get_country())

    def display_references(self):
        pevent = []
        fevent = []
        msg = ""
        for key in self.db.get_person_handles(sort_handles=False):
            p = self.db.get_person_from_handle(key)
            for event_handle in [p.get_birth_handle(), p.get_death_handle()] + p.get_event_list():
                event = self.db.get_event_from_handle(event_handle)
                if event and event.get_place_handle() == self.place.get_handle():
                    pevent.append((p,event))
        for family_handle in self.db.get_family_handles():
            f = self.db.get_family_from_handle(family_handle)
            for event_handle in f.get_event_list():
                event = self.db.get_event_from_handle(event_handle)
                if event and event.get_place_handle() == self.place.get_handle():
                    fevent.append((f,event))

        any = 0
        if len(pevent) > 0:
            any = 1
            msg = msg + _("People") + "\n"
            msg = msg + "_________________________\n\n"
            t = _("%s [%s]: event %s\n")

            for e in pevent:
                msg = msg + ( t % (self.name_display(e[0]),e[0].get_gramps_id(),_(e[1].get_name())))

        if len(fevent) > 0:
            any = 1
            msg = msg + "\n%s\n" % _("Families")
            msg = msg + "_________________________\n\n"
            t = _("%s [%s]: event %s\n")

            for e in fevent:
                father = e[0].get_father_handle()
                mother = e[0].get_mother_handle()
                if father and mother:
                    fname = _("%(father)s and %(mother)s")  % {
                                "father" : self.name_display( self.db.get_person_from_handle( father)),
                                "mother" : self.name_display( self.db.get_person_from_handle( mother)) }
                elif father:
                    fname = self.name_display( self.db.get_person_from_handle( father))
                else:
                    fname = self.name_display( self.db.get_person_from_handle( mother))

                msg = msg + ( t % (fname,e[0].get_gramps_id(),_(e[1].get_name())))

        self.refinfo.get_buffer().set_text(msg)
        if any:
            Utils.bold_label(self.refs_label,self.top)
        else:
            Utils.unbold_label(self.refs_label,self.top)
        
#-------------------------------------------------------------------------
#
# disp_url
#
#-------------------------------------------------------------------------
def disp_url(url):
    return [url.get_path(),url.get_description()]

#-------------------------------------------------------------------------
#
# disp_loc
#
#-------------------------------------------------------------------------
def disp_loc(loc):
    return [loc.get_city(),loc.get_county(),loc.get_state(),loc.get_country()]

#-------------------------------------------------------------------------
#
# DeletePlaceQuery
#
#-------------------------------------------------------------------------
class DeletePlaceQuery:

    def __init__(self,place,db):
        self.db = db
        self.place = place
        
    def query_response(self):
        trans = self.db.transaction_begin()
        self.db.disable_signals()
        
        place_handle = self.place.get_handle()

        for handle in self.db.get_person_handles(sort_handles=False):
            person = self.db.get_person_from_handle(handle)
            if person.has_handle_reference('Place',place_handle):
                person.remove_handle_references('Place',place_handle)
                self.db.commit_person(person,trans)

        for handle in self.db.get_family_handles():
            family = self.db.get_family_from_handle(handle)
            if family.has_handle_reference('Place',place_handle):
                family.remove_handle_references('Place',place_handle)
                self.db.commit_family(family,trans)

        for handle in self.db.get_event_handles():
            event = self.db.get_event_from_handle(handle)
            if event.has_handle_reference('Place',place_handle):
                event.remove_handle_references('Place',place_handle)
                self.db.commit_event(event,trans)

        self.db.enable_signals()
        self.db.remove_place(place_handle,trans)
        self.db.transaction_commit(trans,
                                   _("Delete Place (%s)") % self.place.get_title())

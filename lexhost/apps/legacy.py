from django.http import Http404
from django.shortcuts import redirect
from django.urls import path

from lexhost.apps.exceptions import gone
from lexhost.apps.read import Read


class LegacyPathHandler:

    def __init__(self):
        self.read = Read()

    def legacy(self, request, domain, id_local, sub_id, version='latest'):
        try:
            self.read(domain, id_local, sub_id, version)
        except Http404 as e:
            return gone(request, e)
        return redirect(Read.get_standard_path(domain, id_local, sub_id, version),
                        permanent=True)

    # noinspection PyUnusedLocal
    @staticmethod
    def legacy_gones(request, domain, document_id, sub_id):
        return gone(request)

    @staticmethod
    def paying_my_dues(_, id_local, sub_id):
        """ This is just because I messed up previous canonical tags :/
            So, this is a stupid and annoying type of legacy handling.
            But it's necessary.
        """
        if sub_id.upper().startswith('ARTI'):
            sub_id = 'ART_' + sub_id.split(' ')[1]
        elif sub_id.startswith('Erw') or sub_id.startswith('Rec'):
            sub_id = 'PRE'
        elif sub_id.upper().startswith('ANHANG'):
            splitted = sub_id.split(' ')
            if len(splitted) == 2:
                sub_id = 'ANX_' + splitted[1]
            else:
                sub_id = 'ANX'
        elif sub_id.lower().startswith('fin'):
            sub_id = 'FIN'
        return redirect(f'/eu/{id_local}/{sub_id}/', permanent=True)

    @classmethod
    def register(cls, urlpatterns: list):
        self = cls()
        urlpatterns.extend([
            path('<slug:domain>/<slug:id_local>/<slug:sub_id>/EN/<slug:version>', self.legacy),
            path('<slug:domain>/<slug:id_local>/<slug:sub_id>/EN/', self.legacy),
            path('<slug:domain>/<slug:document_id>/en/<slug:sub_id>/', self.legacy_gones),
            path('<slug:domain>/<slug:document_id>/en/<slug:sub_id>', self.legacy_gones),
            path('<slug:id_local>/<slug:sub_id>/latest', self.paying_my_dues),
        ])

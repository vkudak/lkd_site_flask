from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from flask import current_app, send_file
from flask_login import current_user
from flask_restx import Namespace, Resource

from app.models import Lightcurve, Satellite
from app.sat_utils import lc_to_file


api = Namespace("lightcurves", description="Light curve downloads")


def _download_response(lc_id):
    lc = Lightcurve.get_by_id(lc_id)
    if lc is None:
        return {"message": "Light curve not found"}, 404

    file_data, filename = lc_to_file(lc.id)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv",
    )


def _satellite_archive(satellite, identifier_name, identifier):
    if satellite is None:
        return {"message": f"Satellite with {identifier_name} {identifier} not found"}, 404

    lightcurves = Lightcurve.query.filter_by(sat_id=satellite.id).order_by(
        Lightcurve.ut_start, Lightcurve.id
    ).all()
    if not lightcurves:
        return {"message": "No light curves found for this satellite"}, 404

    archive_buffer = BytesIO()
    with ZipFile(archive_buffer, "w", ZIP_DEFLATED) as archive:
        for lightcurve in lightcurves:
            file_data, filename = lc_to_file(lightcurve.id)
            archive.writestr(f"{lightcurve.id}_{filename}", file_data.getvalue())

    archive_buffer.seek(0)
    return send_file(
        archive_buffer,
        as_attachment=True,
        download_name=f"lightcurves_{identifier_name}_{identifier}.zip",
        mimetype="application/zip",
    )


@api.route("/<int:lc_id>")
class LightcurveDownload(Resource):
    @api.doc(security="SessionAuth", description="Download one light curve by its database ID")
    @api.response(401, "Authentication required")
    @api.response(404, "Light curve not found")
    def get(self, lc_id):
        if not current_user.is_authenticated:
            return {"message": "Authentication required. Please log in."}, 401
        return _download_response(lc_id)


@api.route("/norad/<string:norad>")
class LightcurvesByNorad(Resource):
    @api.doc(security="SessionAuth", description="Download all satellite light curves by NORAD as a ZIP archive")
    @api.response(401, "Authentication required")
    @api.response(404, "Satellite or light curves not found")
    def get(self, norad):
        if not current_user.is_authenticated:
            return {"message": "Authentication required. Please log in."}, 401
        return _satellite_archive(Satellite.get_by_norad(norad), "norad", norad)


@api.route("/cospar/<string:cospar>")
class LightcurvesByCospar(Resource):
    @api.doc(security="SessionAuth", description="Download all satellite light curves by COSPAR as a ZIP archive")
    @api.response(401, "Authentication required")
    @api.response(404, "Satellite or light curves not found")
    def get(self, cospar):
        if not current_user.is_authenticated:
            return {"message": "Authentication required. Please log in."}, 401
        return _satellite_archive(Satellite.get_by_cospar(cospar), "cospar", cospar)
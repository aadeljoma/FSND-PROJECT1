#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
from os import name
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from werkzeug import datastructures
from forms import *
from sqlalchemy.exc import SQLAlchemyError
from models import *
from flasgger import Swagger
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
Swagger(app)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    areas = db.session.query(Venue.city, Venue.state).distinct(
        Venue.city, Venue.state).order_by(Venue.state)
    for area in areas:
        venue_data = []
        data.append({
            'city': area.city,
            'state': area.state,
            'venues': venue_data
        })
        venues = Venue.query.filter(Venue.state == str(area.state)).filter(
            Venue.city == str(area.city)).order_by(Venue.name).all()
        for venue in venues:
            shows = Show.query.filter(
                Show.venue_id == venue.id).all()
            show_list = []
            for show in shows:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if(show.start_time > current_time):
                    show_list.append(show)

            venue_data.append({
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(show_list),
            })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    new_results = db.session.query(Venue).filter(
        Venue.name.ilike(f'%{search_term}%')).all()
    data = []
    for result in new_results:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data.append({
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": len(db.session.query(Show).filter(Show.venue_id == result.id).filter(Show.start_time > current_time).all())
        })
        #
    response = {
        "count": len(new_results),
        "data": data
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    shows = db.session.query(Show, Artist).join(
        Artist).filter(Show.venue_id == venue_id).all()
    past_shows = []
    upcoming_shows = []
    for show, artist in shows:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if(show.start_time > current_time):
            upcoming_shows.append({
                "artist_id": artist.id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": show.start_time
            })
        else:
            past_shows.append({
                "artist_id": artist.id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": show.start_time
            })

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres[1: -1].split(","),
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    """ Create a new venue to the database

    Returns:
        on POST: Redirect to main page after venue has been created.

    """
    form = VenueForm(request.form, meta={'csrf': False})
    if(form.validate()):
        try:
            venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                genres=form.genres.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data
            )
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            flash('An error occurred. Venue ' +
                  form.name.data + ' could not be listed.')
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ': (' + '|'.join(errors) + ')')
        flash('The Venue data is not valid. Please try again!')
    return render_template('pages/home.html')


#  Delete Venue
#  ----------------------------------------------------------------


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash('The venue has been successfully deleted!')
        return render_template('pages/home.html')
    except:
        db.session.rollback()
        flash('Delete was unsuccessful, try again!')
    finally:
        db.session.close()
    return jsonify({'success': True})


#  Update Venue
#  ----------------------------------------------------------------


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    form = VenueForm(request.form)
    try:
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.image_link = form.image_link.data
        venue.facebook_link = form.facebook_link.data
        venue.website_link = form.website_link.data
        venue.genres = form.genres.data
        venue.seeking_talent = form.seeking_talent.data
        venue.seeking_description = form.seeking_description.data
        db.session.commit()
        flash('Venue ' + venue.name +
              ' was successfully updated!')
    except SQLAlchemyError as e:
        print(e)
        db.session.rollback()
        flash('An error occurred. Venue ' +
              venue.name + ' could not be updated.')
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = []
    artists = Artist.query.all()
    for artist in artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    new_results = db.session.query(Artist).filter(
        Artist.name.ilike(f'%{search_term}%')).all()
    data = []
    for result in new_results:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data.append({
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": len(db.session.query(Show).filter(Show.artist_id == result.id).filter(Show.start_time > current_time).all())
        })
    response = {
        "count": len(new_results),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    shows = db.session.query(Show, Venue).join(
        Venue).filter(Show.artist_id == artist_id).all()
    past_shows = []
    upcoming_shows = []
    for show, venue in shows:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if(show.start_time > current_time):
            upcoming_shows.append({
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": show.start_time
            })
        else:
            past_shows.append({
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": show.start_time
            })

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres[1: -1].split(","),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }
    return render_template('pages/show_artist.html', artist=data)

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    """ Create a new artist to the database

    Returns:
        on POST: Redirect to main page after artist has been created.

    """
    form = ArtistForm(request.form, meta={'csrf': False})
    if(form.validate()):
        try:
            artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=form.genres.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data
            )
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!')
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            flash('An error occurred. Artist ' +
                  form.name.data + ' could not be listed.')
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ': (' + '|'.join(errors) + ')')
        flash('The Artist data is not valid. Please try again!')
    return render_template('pages/home.html')


#  Update Artist
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm(request.form)
    try:
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = form.genres.data
        artist.image_link = form.image_link.data
        artist.facebook_link = form.facebook_link.data
        artist.website_link = form.website_link.data
        artist.seeking_venue = form.seeking_venue.data
        artist.seeking_description = form.seeking_description.data
        db.session.commit()
        flash('Artist ' + artist.name +
              ' was successfully updated!')
    except SQLAlchemyError as e:
        print(e)
        db.session.rollback()
        flash('An error occurred. Artist ' +
              artist.name + ' could not be updated.')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = []
    shows = db.session.query(Show, Venue, Artist).join(Venue).join(Artist).all()
    for show, venue, artist in shows:
        data.append({
            "venue_id": venue.id,
            "venue_name": venue.name,
            "artist_id": artist.id,
            "artist_name": artist.name,
            "artist_image_link": artist.image_link,
            "start_time": show.start_time
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    """ Create a new show to the database

    Returns:
        on POST: Redirect to main page after show has been created.

    """
    form = ShowForm(request.form, meta={'csrf': False})
    if(form.validate()):
        try:
            show = Show(
                venue_id=form.venue_id.data,
                artist_id=form.artist_id.data,
                start_time=form.start_time.data
            )
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
        except SQLAlchemyError as e:
            print(e)
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ': (' + '|'.join(errors) + ')')
        flash('The Show data is not valid. Please try again!')
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

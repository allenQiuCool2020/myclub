from django.shortcuts import render, redirect
import calendar
from calendar import HTMLCalendar
from datetime import datetime
import pytz
from .models import Event, Venue
from .forms import VenueForm, EventForm, EventFormAdmin
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.http import HttpResponse
import csv, json
from django.http import JsonResponse

from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.models import User


# Create your views here.
def home(request, year=datetime.now().year, month=datetime.now().strftime('%B')):
    name = "Allen"
    month = month.capitalize()
    # Convert month from name to number
    month_number = list(calendar.month_name).index(month)
    month_number = int(month_number)

    #create a calender 
    cal = HTMLCalendar().formatmonth(year, month_number)
    now = datetime.now(pytz.timezone('Asia/Hong_Kong'))
    
    current_year = now.year
    time = now.strftime('%I:%M:%S %p')

    # Query the events model for dates
    event_list = Event.objects.filter(
        event_date__year = year, 
        event_date__month = month_number,

    )

    context = {"name":"Allen", "year": year, "month":month, 
    "month_number": month_number, "cal": cal, "current_year":current_year, "time":time, 'event_list': event_list}
    return render(request, 'events/home.html', context)

def all_events(request):
    event_list = Event.objects.all().order_by('-event_date')
    context = {'event_list':event_list}
    return render(request, 'events/event_list.html', context=context)

def add_venue(request):
    submitted = False
    if request.method == 'POST':
        form = VenueForm(request.POST, request.FILES)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user.id # logged in user
            venue.save()
            # form.save()
            return HttpResponseRedirect('/add_venue?submitted=True')
    else:
        form = VenueForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form': form, 'submitted': submitted}
    return render(request,'events/add_venue.html', context)

def list_venues(request):
    # venue_list = Venue.objects.all().order_by('name')
    venue_list = Venue.objects.all().order_by('name')

    # Set up Pagination
    p = Paginator(venue_list, 5)
    page = request.GET.get('page')
    venues = p.get_page(page)
    nums = "A" * venues.paginator.num_pages

    context = {'venue_list':venue_list, "venues": venues, "nums": nums}
    return render(request, 'events/venue.html', context=context)

def show_venues(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    venue_owner = User.objects.get(pk=venue.owner)
    events = venue.event_set.all()
    context = {'venue':venue, 'venue_owner': venue_owner, 'events':events}
    return render(request, 'events/show_venue.html', context)

def search_venues(request):
    if request.method == "POST":   
        searched = request.POST['searched'] 
        venues = Venue.objects.filter(name__contains=searched)
        context = {'searched': searched, 'venues': venues}
        return render(request, 'events/search_venue.html', context)
    else:
        return render(request, 'events/search_venue.html')

def search_event(request):
    query = request.GET.get('q')
    qs = Event.objects.all()
    if query is not None:
        lookups = Q(name__icontains=query) | Q(description__icontains=query)
        qs = Event.objects.filter(lookups)
    context = {"event_list": qs}
    return render(request, 'events/search_event.html', context=context)

def update_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    form = VenueForm(request.POST or None,request.FILES or None, instance=venue)
    if form.is_valid():
        form.save()
        return redirect('list-venues')
    context = {'venue':venue, "form": form}
    return render(request, 'events/update_venue.html', context=context)

def add_event(request):
    submitted = False
    if request.method == 'POST':
        if request.user.is_superuser:
            form = EventFormAdmin(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/add_event?submitted=True')
        else:
            form = EventForm(request.POST)          
            if form.is_valid():
                # form.save()
                event = form.save(commit=False)
                event.manager = request.user
                event.save()
                return HttpResponseRedirect('/add_event?submitted=True')
    else:
        # Just going to the page, not submitting
        if request.user.is_superuser:
            form = EventFormAdmin
        else:
            form = EventForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form': form, 'submitted': submitted}
    return render(request,'events/add_event.html', context=context)

def my_events(request):
    if request.user.is_authenticated:
        me = request.user.id
        events = Event.objects.filter(attendees=me)
        context = {'events': events}
        return render(request, 'events/my_events.html', context=context)
    else:
        messages.success(request, ('You Are Not Authorized To View This Page'))
        return redirect('home')




def update_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user.is_superuser:
        form = EventFormAdmin(request.POST or None, instance=event)
    else:
        form = EventForm(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        return redirect('list-events')
    context = {'event':event, "form": form}
    return render(request, 'events/update_event.html', context=context)

def delete_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user == event.manager:
        event.delete()
        messages.success(request, ('Event Had Been Deleted'))
        return redirect('list-events')
    else:
        messages.success(request, ('You Are Not Authorized To Delete This Event'))
        return redirect('list-events')

def delete_venue(request, venue_id):
    event = Venue.objects.get(pk=venue_id)
    event.delete()
    return redirect('list-venues')

# Generate text file venue list
def venue_text(request):
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=venues.txt'
    # Designate the model
    venues = Venue.objects.all()
    lines = []
    for venue in venues:
        lines.append(f'{venue.name}\n{venue.address}\n{venue.zip_code}\n{venue.phone}\n{venue.web}\n{venue.email_address}\n\n\n')
    # lines = ['This is a test\n',
    # 'This is a test2\n',
    # 'This is a test3\n'
    # ]
    # Write to text file
    response.writelines(lines)
    return response

def venue_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=venues.csv'
    # Create a csv writer
    writer = csv.writer(response)
    # Designate the model
    venues = Venue.objects.all()

    # Add column headings to the csv file
    writer.writerow(['Venue name', 'Address','Zip code', 'Phone', 'Web Address', 'Email Address'])
    

    for venue in venues:
        writer.writerow([venue.name, venue.address, venue.zip_code, venue.phone,venue.web, venue.email_address])

 
    return response

def venue_json(request):
    # Designate the model and create json data
    json_data = list(Venue.objects.values())
    response = JsonResponse(json_data, safe=False)
    response['Content-Type'] = 'application/force-download'
    return response
    # return HttpResponse(json.dumps(json_data), content_type="application/json")
    # return JsonResponse(json_data, safe=False)

def venue_pdf(request):
    # Create Bytestream buffer
    buf = io.BytesIO()
    # Create a canvas
    c = canvas.Canvas(buf, pagesize=letter,bottomup=0)
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    # Add some lines of text
    # lines = [
    #     "test1",
    #     "test2",
    #     "test3",
    # ]
    venues = Venue.objects.all()
    lines = []
    for venue in venues:
        lines.append(venue.name)
        lines.append(venue.address)
        lines.append(venue.zip_code)
        lines.append(venue.phone)
        lines.append(venue.web)
        lines.append(venue.email_address)
        lines.append(" ")

    # loop
    for line in lines:
        textob.textLine(line)

    # Finish up
    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)

    # Return something
    return FileResponse(buf, as_attachment=True, filename='venue.pdf')
    

def admin_approval(request):
    # Get the venues
    venue_list = Venue.objects.all()
    event_count = Event.objects.all().count()
    venue_count = Venue.objects.all().count()
    user_count = User.objects.all().count()
    event_list = Event.objects.all().order_by('-event_date')
    if request.user.is_superuser:
        if request.method == 'POST':
            id_list = request.POST.getlist('boxes')
            # Uncheck all events
            event_list.update(approved=False)
            # print(id_list)
            # Update the database
            for i in id_list:
                Event.objects.filter(pk=int(i)).update(approved=True)

            messages.success(request, ('Event Approval Has Been Updated'))
            return redirect('list-events')
        else:
            context = {'event_list': event_list, 'event_count': event_count, 'venue_count': venue_count,                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
            'user_count': user_count, 'venue_list': venue_list}
            return render(request, 'events/admin_approval.html', context=context)
    else:
        messages.success(request, ('You Are Not Authorized To View This Page'))
        return redirect('home')
    
    
    return render(request, 'events/admin_approval.html')


def venue_events(request, venue_id):
    # Get the venue
    venue = Venue.objects.get(id=venue_id)
    events = venue.event_set.all()
    if events:    
        context = {'venue': venue, 'events': events}
        return render(request, 'events/venue_events.html', context=context)
    else:
        messages.warning(request, ('This are no events for this venue'))
        return redirect('admin_approval')


# Show Event
def show_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    context = {'event':event}
    return render(request, 'events/show_event.html', context=context)
    
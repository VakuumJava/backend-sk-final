"""
API представления для календаря и расписания
"""
from .utils import *


# ----------------------------------------
#  Календарь и события
# ----------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_events(request):
    """
    GET /mine/
    Returns all events for the authenticated user.
    """
    events = CalendarEvent.objects.filter(master=request.user)
    serializer = CalendarEventSerializer(events, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event(request):
    """
    POST /create/
    Creates a new event. Expects title, start, end, color (optional) in body.
    """
    serializer = CalendarEventSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(master=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_event_time(request, event_id):
    """
    PUT /update/{event_id}/
    Updates start/end of an existing event (used for drag/resize).
    """
    try:
        event = CalendarEvent.objects.get(id=event_id, master=request.user)
    except CalendarEvent.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    data = {}
    if 'start' in request.data:
        data['start'] = request.data['start']
    if 'end' in request.data:
        data['end'] = request.data['end']

    serializer = CalendarEventSerializer(event, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_event(request, event_id):
    """
    DELETE /delete/{event_id}/
    Deletes an event after user confirmation.
    """
    try:
        event = CalendarEvent.objects.get(id=event_id, master=request.user)
    except CalendarEvent.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    event.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------------------------------
#  Контакты
# ----------------------------------------

@api_view(['GET'])
def get_all_contacts(request):
    contacts = Contact.objects.all()
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_contact(request):
    serializer = ContactSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_contact(request, contact_id):
    try:
        contact = Contact.objects.get(id=contact_id)
        contact.delete()
        return Response({'message': 'Contact deleted successfully'}, status=status.HTTP_200_OK)
    except Contact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def mark_as_called(request, contact_id):
    try:
        contact = Contact.objects.get(id=contact_id)
        contact.status = 'обзвонен'
        contact.save()
        serializer = ContactSerializer(contact)
        return Response(serializer.data)
    except Contact.DoesNotExist:
        return Response({'detail': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_called_contacts(request):
    contacts = Contact.objects.filter(status='обзвонен')
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_uncalled_contacts(request):
    contacts = Contact.objects.filter(status='не обзвонен')
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)

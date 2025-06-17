from rest_framework import serializers
from .models import Booking
from cars.serializers import CarSerializer  # optional for nested car info
from rest_framework.response import Response
from rest_framework import serializers
from .models import Report
from users.models import User
from cars.models import Car
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class BookingSerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    reported_user_id = serializers.IntegerField(required=False, allow_null=True)
    reported_car_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Report
        fields = ['report_type', 'reason', 'reported_user_id', 'reported_car_id']

    def validate(self, data):
        report_type = data.get('report_type')
        if report_type == 'user' and not data.get('reported_user_id'):
            raise serializers.ValidationError({"reported_user_id": "This field is required when report_type is 'user'."})
        if report_type == 'car' and not data.get('reported_car_id'):
            raise serializers.ValidationError({"reported_car_id": "This field is required when report_type is 'car'."})
        return data

    def create(self, validated_data):
        reporter = self.context['request'].user
        report_type = validated_data['report_type']
        reason = validated_data['reason']

        reported_user = None
        reported_car = None

        if report_type == 'user':
            reported_user = User.objects.get(id=validated_data['reported_user_id'])
        elif report_type == 'car':
            reported_car = Car.objects.get(id=validated_data['reported_car_id'])

        return Report.objects.create(
            reporter=reporter,
            report_type=report_type,
            reason=reason,
            reported_user=reported_user,
            reported_car=reported_car,
        )



class BookingCreateSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be before or equal to end_date.")

        try:
            car = Car.objects.get(id=data['car_id'], status='available')
        except Car.DoesNotExist:
            raise serializers.ValidationError("Car not found or not available.")

        # Check overlapping bookings
        overlapping = Booking.objects.filter(
            car=car,
            status__in=['pending', 'approved'],
            start_date__lte=data['end_date'],
            end_date__gte=data['start_date']
        )
        if overlapping.exists():
            raise serializers.ValidationError("Car is already booked for the selected dates.")

        data['car'] = car
        return data

    def create(self, validated_data):
        car = validated_data['car']
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']

        days = (end_date - start_date).days + 1
        total_cost = car.daily_rate * Decimal(days)
        platform_fee = total_cost * Decimal('0.10')
        owner_payout = total_cost - platform_fee

        booking = Booking.objects.create(
            user=self.context['request'].user,
            car=car,
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost,
            platform_fee=platform_fee,
            owner_payout=owner_payout,
            status='approved' if car.auto_approve_bookings else 'pending'
        )
        return booking



    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            booking = serializer.save()
            return Response({
                "message": "Booking created successfully.",
                "booking_id": booking.id,
                "status": booking.status,
                "total_cost": str(booking.total_cost),
                "platform_fee": str(booking.platform_fee),
                "owner_payout": str(booking.owner_payout)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
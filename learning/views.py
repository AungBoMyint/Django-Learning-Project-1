from django.shortcuts import render
from django.db.models import Count,Avg
from rest_framework import status
from django.db import transaction
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.shortcuts import get_list_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet,GenericViewSet,ModelViewSet
from rest_framework.mixins import RetrieveModelMixin,ListModelMixin,UpdateModelMixin,CreateModelMixin
from rest_framework.filters import SearchFilter
from . import filters
from .permissions import IsCurrentUserOrReadOnly
from rest_framework.permissions import AllowAny,IsAuthenticated
from . import models
from . import serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import api_view,permission_classes
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
# Create your views here.
class CategoryViewSet(ReadOnlyModelViewSet):
    queryset = models.Category.objects.annotate(
        subcategories_count = Count('subcategories',distinct=True),
        subcategories_topics_count = Count("subcategories__topics",distinct=True)
    ).all()
    serializer_class = serializers.CategorySerializer
    filter_backends = [DjangoFilterBackend]
    

class SubCategoryViewSet(ReadOnlyModelViewSet):
    queryset = models.SubCategory.objects.annotate(
        topics_count = Count("topics")
    ).all()
    serializer_class = serializers.SubCategorySerializer

class TopicViewSet(ReadOnlyModelViewSet):
    queryset = models.Topic.objects.annotate(
        courses_count = Count('courses')
    ).all()
    serializer_class = serializers.TopicSerializer

class CourseViewSet(RetrieveModelMixin,UpdateModelMixin,ListModelMixin,GenericViewSet):
    
    serializer_class = serializers.CourseSerializer
    filter_backends = [DjangoFilterBackend,SearchFilter]
    filterset_class = filters.CourseFilter
    search_fields = ["title"]

    #---------------------For Caching-----------
    @method_decorator(cache_page(5 * 60))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    #--------------------------
    def get_serializer_context(self):
        return {'user_id':self.request.user.id}
    def get_queryset(self):
        return models.Course.objects \
    .annotate(
        enroll_students_count=Count('enroll_students',distinct=True),
        ratings_avg = Avg('ratings__rating',distinct=True),
        reviews_count = Count('reviews',distinct=True)
        ) \
    .prefetch_related('ratings') \
    .prefetch_related('reviews') \
    .select_related('discount_item__discount') \
    .prefetch_related('enroll_students__student__user') \
    .prefetch_related('topic__subcategory') \
    .prefetch_related('sections__subsections__video') \
    .prefetch_related('sections__subsections__blog') \
    .prefetch_related('sections__subsections__pdf').all()
        

class DiscountViewSet(ReadOnlyModelViewSet):
    queryset = models.Discount.objects \
    .annotate(
        enroll_students_count = Count('discount_items__course__enroll_students')
    ) \
    .prefetch_related(
        "discount_items__course__sections"
        ).all()
    serializer_class = serializers.DiscountSerializer

class SubSectionViewSet(ReadOnlyModelViewSet):
    queryset = models.SubSection.objects.prefetch_related("video") \
    .prefetch_related("blog") \
    .prefetch_related("pdf") \
    .all()
    serializer_class = serializers.SubSectionSerializer

class SliderViewSet(ReadOnlyModelViewSet):
    queryset = models.Slider.objects.prefetch_related(
        "messengerlink",
        "courselink",
        "facebooklink",
        "youtube"
    ).all()
    serializer_class = serializers.SliderSerializer

class StudentViewSet(ListModelMixin,CreateModelMixin,RetrieveModelMixin,GenericViewSet):
    queryset = models.Student.objects.select_related('user').all()
    serializer_class = serializers.StudentSerializer

    def get_serializer_context(self):
        return {'user_id':self.request.user.id}
    
    @action(detail=False,methods=['GET'])
    def enrolled_courses(self,request):
        enrollment = models.EnrollStudents.objects.filter(student__user__id=request.user.id)
        serializer = serializers.EnrollCourseSerializer(enrollment,many=True)
        return Response(serializer.data)

    @action(detail=False,methods=['GET','PUT'],permission_classes=[IsAuthenticated])
    def me(self,request):
        if request.method == 'GET':
            student = models.Student.objects.get(user_id=request.user.id)
            serializer = serializers.StudentSerializer(student)
            return Response(serializer.data)
        elif request.method == 'PUT':
            student = models.Student.objects.get(user_id=request.user.id)
            serializer = serializers.StudentSerializer(student,data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

class EnrollmentViewSet(CreateModelMixin,GenericViewSet,RetrieveModelMixin):
    queryset = models.Enrollment.objects.prefetch_related('enroll_students').all()
    serializer_class = serializers.EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        #check enroll_students is empty or not
        enroll_students = request.data.get("enroll_students",[])
        if len(enroll_students) < 1:
            return Response({"enroll_students":"Enroll Students shouldn't be empty"},status=status.HTTP_400_BAD_REQUEST)
        #if not empty
        with transaction.atomic():
            #first we save Enrollment
            enrollment = models.Enrollment.objects.create()
            #second we loop and save enroll_students
            
            for course_id in enroll_students:
                models.EnrollStudents.objects.create(
                                    enrollment_id = enrollment.id,
                                    course_id = course_id,
                                    student_id = request.user.student.id
                                )
                
            #then return enrollment
        serializer = serializers.EnrollmentSerializer(enrollment)
        return Response(serializer.data)
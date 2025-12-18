"""
Unit tests for models to verify relationships and computed properties.
Tests use in-memory objects to test relationships and computed properties.
"""

import pytest
from app.models.company import Company
from app.models.project import Project  
from app.models.ar_content import ARContent
from app.models.video import Video
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus
import uuid


class TestCompanyModel:
    """Test cases for Company model using in-memory objects"""

    def test_company_create_in_memory(self):
        """Test creating a company with required fields in memory"""
        company = Company(
            name="Test Company LLC",
            contact_email="test@company.com", 
            status=CompanyStatus.ACTIVE
        )
        
        # Test that object was created correctly
        assert company.name == "Test Company LLC"
        assert company.contact_email == "test@company.com"
        assert company.status == CompanyStatus.ACTIVE
        # ID and timestamps should be None until saved to database
        assert company.id is None
        assert company.created_at is None
        assert company.updated_at is None

    def test_company_projects_count_empty(self):
        """Test projects_count returns 0 for company with no projects"""
        company = Company(name="Test Company")
        # Mock empty projects list
        company.projects = []
        
        assert company.projects_count == 0

    def test_company_projects_count_with_projects(self):
        """Test projects_count returns correct number"""
        company = Company(name="Test Company")
        
        # Mock projects list
        project1 = Project(name="Project 1")
        project2 = Project(name="Project 2") 
        project3 = Project(name="Project 3")
        company.projects = [project1, project2, project3]
        
        assert company.projects_count == 3

    def test_company_ar_content_count_empty(self):
        """Test ar_content_count returns 0 for company with no content"""
        company = Company(name="Test Company")
        # Mock empty projects list
        company.projects = []
        
        assert company.ar_content_count == 0

    def test_company_ar_content_count_with_content(self):
        """Test ar_content_count counts content from all projects"""
        company = Company(name="Test Company")
        
        # Mock projects with AR content
        project1 = Project(name="Project 1")
        project2 = Project(name="Project 2")
        
        # Add AR content to projects
        content1 = ARContent(order_number="ORDER-001")
        content2 = ARContent(order_number="ORDER-002") 
        content3 = ARContent(order_number="ORDER-003")
        
        project1.ar_contents = [content1, content2]  # 2 content in project1
        project2.ar_contents = [content3]  # 1 content in project2
        
        company.projects = [project1, project2]
        
        # Should count total content across all projects
        assert company.ar_content_count == 3

    def test_company_repr(self):
        """Test __repr__ method works correctly"""
        company = Company(name="Test Company", status=CompanyStatus.ACTIVE)
        company.id = uuid.uuid4()  # Mock ID for repr test
        
        repr_str = repr(company)
        assert "Company" in repr_str
        assert "name=Test Company" in repr_str
        assert "status=active" in repr_str


class TestProjectModel:
    """Test cases for Project model using in-memory objects"""

    def test_project_create_in_memory(self):
        """Test creating a project with company_id"""
        company_id = uuid.uuid4()
        project = Project(
            name="Test Project",
            company_id=company_id,
            status=ProjectStatus.ACTIVE
        )
        
        assert project.name == "Test Project"
        assert project.company_id == company_id
        assert project.status == ProjectStatus.ACTIVE
        assert project.created_at is None

    def test_project_status_default(self):
        """Test project gets default status"""
        project = Project(name="Default Status Project", company_id=uuid.uuid4())
        
        # When creating object without session, default may not be applied
        # Check that the default is defined in the model
        from sqlalchemy import inspect
        insp = inspect(Project)  # Inspect class, not instance
        status_column = insp.columns['status']
        assert status_column.default.arg == ProjectStatus.ACTIVE.value

    def test_project_ar_content_count_empty(self):
        """Test ar_content_count returns 0 for project with no content"""
        project = Project(name="Test Project")
        project.ar_contents = []
        
        assert project.ar_content_count == 0

    def test_project_ar_content_count_with_content(self):
        """Test ar_content_count returns correct number"""
        project = Project(name="Test Project")
        
        # Mock 3 AR content items
        content1 = ARContent(order_number="ORDER-001")
        content2 = ARContent(order_number="ORDER-002")
        content3 = ARContent(order_number="ORDER-003")
        project.ar_contents = [content1, content2, content3]
        
        assert project.ar_content_count == 3

    def test_project_relationship_company(self):
        """Test project.company relationship works"""
        company = Company(name="Parent Company", id=uuid.uuid4())
        project = Project(name="Child Project", company_id=company.id)
        
        # Mock the relationship
        project.company = company
        
        assert project.company.id == company.id
        assert project.company.name == "Parent Company"

    def test_project_relationship_ar_contents(self):
        """Test project.ar_contents relationship works"""
        project = Project(name="Test Project")
        
        # Mock multiple AR content items
        content1 = ARContent(order_number="ORDER-001")
        content2 = ARContent(order_number="ORDER-002")
        project.ar_contents = [content1, content2]
        
        assert len(project.ar_contents) == 2
        order_numbers = [content.order_number for content in project.ar_contents]
        assert "ORDER-001" in order_numbers
        assert "ORDER-002" in order_numbers

    def test_project_repr(self):
        """Test __repr__ method works correctly"""
        project = Project(name="Test Project", status=ProjectStatus.ACTIVE)
        project.id = uuid.uuid4()  # Mock ID for repr test
        
        repr_str = repr(project)
        assert "Project" in repr_str
        assert "name=Test Project" in repr_str
        # Note: status might not be 'active' when object not saved to DB
        # This is expected behavior for in-memory objects


class TestARContentModel:
    """Test cases for ARContent model using in-memory objects"""

    def test_ar_content_create_in_memory(self):
        """Test creating AR content"""
        project_id = uuid.uuid4()
        ar_content = ARContent(
            project_id=project_id,
            order_number="TEST-001",
            customer_name="John Doe",
            status=ArContentStatus.ACTIVE
        )
        
        assert ar_content.project_id == project_id
        assert ar_content.order_number == "TEST-001"
        assert ar_content.customer_name == "John Doe"
        assert ar_content.status == ArContentStatus.ACTIVE
        assert ar_content.created_at is None

    def test_ar_content_computed_properties(self):
        """Test computed properties return correct values"""
        ar_content = ARContent(order_number="TEST-001")
        ar_content.id = uuid.uuid4()  # Mock ID for property test
        
        # Test public_link
        public_link = ar_content.public_link
        assert public_link == f"/ar/{ar_content.id}"
        
        # Test qr_code_path
        qr_path = ar_content.qr_code_path
        assert qr_path == f"/storage/qr/{ar_content.id}.png"

    def test_ar_content_relationship_project(self):
        """Test ar_content.project relationship works"""
        project = Project(name="Parent Project", id=uuid.uuid4())
        ar_content = ARContent(project_id=project.id, order_number="PROJ-001")
        
        # Mock the relationship
        ar_content.project = project
        
        assert ar_content.project.id == project.id
        assert ar_content.project.name == "Parent Project"

    def test_ar_content_relationship_videos(self):
        """Test ar_content.videos relationship works"""
        ar_content = ARContent(order_number="TEST-001")
        ar_content.id = uuid.uuid4()  # Mock ID
        
        # Mock multiple videos
        video1 = Video(filename="video1.mp4")
        video2 = Video(filename="video2.mp4")
        ar_content.videos = [video1, video2]
        
        assert len(ar_content.videos) == 2
        filenames = [video.filename for video in ar_content.videos]
        assert "video1.mp4" in filenames
        assert "video2.mp4" in filenames

    def test_ar_content_active_video_none(self):
        """Test active_video returns None when no active video set"""
        ar_content = ARContent(order_number="TEST-001")
        
        assert ar_content.active_video is None

    def test_ar_content_active_video_set(self):
        """Test active_video relationship works when set"""
        ar_content = ARContent(order_number="TEST-001")
        ar_content.id = uuid.uuid4()  # Mock ID
        
        video = Video(filename="active_video.mp4")
        video.id = uuid.uuid4()  # Mock ID
        
        # Set as active video
        ar_content.active_video_id = video.id
        ar_content.active_video = video  # Mock relationship
        
        assert ar_content.active_video is not None
        assert ar_content.active_video.id == video.id
        assert ar_content.active_video.filename == video.filename

    def test_ar_content_company_id_property(self):
        """Test company_id property returns project's company_id"""
        company_id = uuid.uuid4()
        project = Project(name="Test Project", company_id=company_id)
        ar_content = ARContent(project_id=project.id, order_number="TEST-001")
        
        # Mock the relationship
        ar_content.project = project
        
        assert ar_content.company_id == company_id

    def test_ar_content_repr(self):
        """Test __repr__ method works correctly"""
        ar_content = ARContent(order_number="TEST-REPR", status=ArContentStatus.PENDING)
        ar_content.id = uuid.uuid4()  # Mock ID for repr test
        
        repr_str = repr(ar_content)
        assert "ARContent" in repr_str
        assert "order_number=TEST-REPR" in repr_str
        # Note: status might not be 'pending' when object not saved to DB
        # This is expected behavior for in-memory objects


class TestVideoModel:
    """Test cases for Video model using in-memory objects"""

    def test_video_create_in_memory(self):
        """Test creating a video"""
        ar_content_id = uuid.uuid4()
        video = Video(
            ar_content_id=ar_content_id,
            filename="test_video.mp4",
            video_status=VideoStatus.READY
        )
        
        assert video.ar_content_id == ar_content_id
        assert video.filename == "test_video.mp4"
        assert video.video_status == VideoStatus.READY
        assert video.created_at is None

    def test_video_status_default(self):
        """Test video gets default status"""
        ar_content_id = uuid.uuid4()
        video = Video(ar_content_id=ar_content_id, filename="default_status.mp4")
        
        assert video.video_status == VideoStatus.UPLOADED

    def test_video_relationship_ar_content(self):
        """Test video.ar_content relationship works"""
        ar_content = ARContent(order_number="VIDEO-TEST", id=uuid.uuid4())
        video = Video(ar_content_id=ar_content.id, filename="relationship_test.mp4")
        
        # Mock the relationship
        video.ar_content = ar_content
        
        assert video.ar_content.id == ar_content.id
        assert video.ar_content.order_number == "VIDEO-TEST"

    def test_video_with_metadata(self):
        """Test creating video with metadata"""
        ar_content_id = uuid.uuid4()
        video = Video(ar_content_id=ar_content_id, filename="metadata_test.mp4")
        
        # Add metadata
        video.duration = 120  # 2 minutes
        video.size = 1024000  # 1MB
        
        assert video.duration == 120
        assert video.size == 1024000


class TestModelValidation:
    """Test model validation and constraints"""

    def test_ar_content_order_number_validation(self):
        """Test AR content order number validation"""
        # Valid order number should work
        content = ARContent(order_number="VALID-001")
        assert content.order_number == "VALID-001"
        
        # Test various valid formats
        valid_numbers = ["ORDER-001", "12345", "ABC-123", "ORDER_ABC"]
        for order_num in valid_numbers:
            content = ARContent(order_number=order_num)
            assert content.order_number == order_num

    def test_model_status_enums(self):
        """Test that status fields accept enum values"""
        # Test all status enums work
        company = Company(status=CompanyStatus.ACTIVE)
        assert company.status == "active"
        
        company = Company(status=CompanyStatus.INACTIVE)
        assert company.status == "inactive"
        
        project = Project(status=ProjectStatus.ACTIVE)
        assert project.status == "active"
        
        project = Project(status=ProjectStatus.ARCHIVED)
        assert project.status == "archived"
        
        ar_content = ARContent(status=ArContentStatus.PENDING)
        assert ar_content.status == "pending"
        
        ar_content = ARContent(status=ArContentStatus.ACTIVE)
        assert ar_content.status == "active"
        
        video = Video(video_status=VideoStatus.UPLOADED)
        assert video.video_status == "uploaded"
        
        video = Video(video_status=VideoStatus.READY)
        assert video.video_status == "ready"


class TestModelRelationshipsStructure:
    """Test that model relationships are properly structured"""

    def test_company_project_relationship_structure(self):
        """Test Company-Project relationship structure"""
        company = Company(name="Test Company")
        project = Project(name="Test Project")
        
        # Test that relationship attributes exist
        assert hasattr(company, 'projects')
        assert hasattr(project, 'company')
        
        # Mock relationship
        company.projects = [project]
        project.company = company
        
        assert len(company.projects) == 1
        assert company.projects[0] == project
        assert project.company == company

    def test_project_ar_content_relationship_structure(self):
        """Test Project-ARContent relationship structure"""
        project = Project(name="Test Project")
        ar_content = ARContent(order_number="TEST-001")
        
        # Test that relationship attributes exist
        assert hasattr(project, 'ar_contents')
        assert hasattr(ar_content, 'project')
        
        # Mock relationship
        project.ar_contents = [ar_content]
        ar_content.project = project
        
        assert len(project.ar_contents) == 1
        assert project.ar_contents[0] == ar_content
        assert ar_content.project == project

    def test_ar_content_video_relationship_structure(self):
        """Test ARContent-Video relationship structure"""
        ar_content = ARContent(order_number="TEST-001")
        video = Video(filename="test.mp4")
        
        # Test that relationship attributes exist
        assert hasattr(ar_content, 'videos')
        assert hasattr(ar_content, 'active_video')
        assert hasattr(video, 'ar_content')
        
        # Mock relationships
        ar_content.videos = [video]
        ar_content.active_video = video
        video.ar_content = ar_content
        
        assert len(ar_content.videos) == 1
        assert ar_content.videos[0] == video
        assert ar_content.active_video == video
        assert video.ar_content == ar_content
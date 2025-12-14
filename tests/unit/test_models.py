"""
Unit tests for models to verify relationships and computed properties.

Tests include:
- Computed properties (projects_count, ar_content_count)
- Default statuses
- Relationships and cascade operations
- Enum validation
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project  
from app.models.ar_content import ARContent
from app.models.video import Video
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus


@pytest.mark.asyncio
class TestCompany:
    """Test cases for Company model"""

    async def test_company_create(self, test_session: AsyncSession, company_factory):
        """Test creating a company with required fields"""
        company = await company_factory(
            test_session,
            name="Test Company LLC",
            contact_email="test@company.com", 
            status=CompanyStatus.ACTIVE
        )
        
        await test_session.commit()
        await test_session.refresh(company)
        
        assert company.id is not None
        assert company.name == "Test Company LLC"
        assert company.contact_email == "test@company.com"
        assert company.status == CompanyStatus.ACTIVE
        assert company.created_at is not None
        assert company.updated_at is not None

    async def test_company_projects_count_empty(self, test_session: AsyncSession, company_factory):
        """Test projects_count returns 0 for company with no projects"""
        company = await company_factory(test_session)
        await test_session.commit()
        
        assert company.projects_count == 0

    async def test_company_projects_count_with_projects(self, test_session: AsyncSession, company_factory, project_factory):
        """Test projects_count returns correct number"""
        company = await company_factory(test_session)
        
        # Create 3 projects for this company
        for i in range(3):
            await project_factory(test_session, company_id=company.id)
        
        await test_session.commit()
        await test_session.refresh(company)
        
        assert company.projects_count == 3

    async def test_company_ar_content_count_empty(self, test_session: AsyncSession, company_factory):
        """Test ar_content_count returns 0 for company with no content"""
        company = await company_factory(test_session)
        await test_session.commit()
        
        assert company.ar_content_count == 0

    async def test_company_ar_content_count_with_content(self, test_session: AsyncSession, company_factory, project_factory, ar_content_factory):
        """Test ar_content_count counts content from all projects"""
        company = await company_factory(test_session)
        
        # Create 2 projects with different amounts of content
        project1 = await project_factory(test_session, company_id=company.id)
        project2 = await project_factory(test_session, company_id=company.id)
        
        # Add content to projects
        await ar_content_factory(test_session, project_id=project1.id)
        await ar_content_factory(test_session, project_id=project1.id)  # 2 content in project1
        await ar_content_factory(test_session, project_id=project2.id)  # 1 content in project2
        
        await test_session.commit()
        await test_session.refresh(company)
        
        # Should count total content across all projects
        assert company.ar_content_count == 3

    async def test_company_repr(self, test_session: AsyncSession, company_factory):
        """Test __repr__ method works correctly"""
        company = await company_factory(test_session, name="Test Company")
        await test_session.commit()
        await test_session.refresh(company)
        
        repr_str = repr(company)
        assert "Company" in repr_str
        assert f"id={company.id}" in repr_str
        assert "name=Test Company" in repr_str
        assert f"status={company.status}" in repr_str

    async def test_company_relationships(self, test_session: AsyncSession, company_factory, project_factory):
        """Test company.projects relationship works"""
        company = await company_factory(test_session)
        project = await project_factory(test_session, company_id=company.id)
        
        await test_session.commit()
        await test_session.refresh(company)
        
        # Test relationship
        assert len(company.projects) == 1
        assert company.projects[0].id == project.id
        assert company.projects[0].company_id == company.id


@pytest.mark.asyncio
class TestProject:
    """Test cases for Project model"""

    async def test_project_create(self, test_session: AsyncSession, project_factory, company_factory):
        """Test creating a project with company_id"""
        company = await company_factory(test_session)
        project = await project_factory(
            test_session,
            name="Test Project",
            company_id=company.id,
            status=ProjectStatus.ACTIVE
        )
        
        await test_session.commit()
        await test_session.refresh(project)
        
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.company_id == company.id
        assert project.status == ProjectStatus.ACTIVE
        assert project.created_at is not None

    async def test_project_status_default(self, test_session: AsyncSession, company_factory):
        """Test project gets default status"""
        company = await company_factory(test_session)
        project = Project(name="Default Status Project", company_id=company.id)
        
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)
        
        assert project.status == ProjectStatus.ACTIVE

    async def test_project_ar_content_count_empty(self, test_session: AsyncSession, project_factory):
        """Test ar_content_count returns 0 for project with no content"""
        project = await project_factory(test_session)
        await test_session.commit()
        
        assert project.ar_content_count == 0

    async def test_project_ar_content_count_with_content(self, test_session: AsyncSession, project_factory, ar_content_factory):
        """Test ar_content_count returns correct number"""
        project = await project_factory(test_session)
        
        # Create 3 AR content items
        for i in range(3):
            await ar_content_factory(test_session, project_id=project.id)
        
        await test_session.commit()
        await test_session.refresh(project)
        
        assert project.ar_content_count == 3

    async def test_project_relationship_company(self, test_session: AsyncSession, project_factory, company_factory):
        """Test project.company relationship works"""
        company = await company_factory(test_session, name="Parent Company")
        project = await project_factory(test_session, company_id=company.id, name="Child Project")
        
        await test_session.commit()
        await test_session.refresh(project)
        
        assert project.company.id == company.id
        assert project.company.name == "Parent Company"

    async def test_project_relationship_ar_contents(self, test_session: AsyncSession, project_factory, ar_content_factory):
        """Test project.ar_contents relationship works"""
        project = await project_factory(test_session)
        
        # Create multiple AR content items
        content1 = await ar_content_factory(test_session, project_id=project.id, order_number="ORDER-001")
        content2 = await ar_content_factory(test_session, project_id=project.id, order_number="ORDER-002")
        
        await test_session.commit()
        await test_session.refresh(project)
        
        assert len(project.ar_contents) == 2
        order_numbers = [content.order_number for content in project.ar_contents]
        assert "ORDER-001" in order_numbers
        assert "ORDER-002" in order_numbers

    async def test_project_repr(self, test_session: AsyncSession, project_factory):
        """Test __repr__ method works correctly"""
        project = await project_factory(test_session, name="Test Project")
        await test_session.commit()
        await test_session.refresh(project)
        
        repr_str = repr(project)
        assert "Project" in repr_str
        assert f"id={project.id}" in repr_str
        assert "name=Test Project" in repr_str
        assert f"status={project.status}" in repr_str


@pytest.mark.asyncio
class TestARContent:
    """Test cases for ARContent model"""

    async def test_ar_content_create(self, test_session: AsyncSession, ar_content_factory, project_factory):
        """Test creating AR content"""
        project = await project_factory(test_session)
        ar_content = await ar_content_factory(
            test_session,
            project_id=project.id,
            order_number="TEST-001",
            customer_name="John Doe",
            status=ArContentStatus.ACTIVE
        )
        
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.id is not None
        assert ar_content.project_id == project.id
        assert ar_content.order_number == "TEST-001"
        assert ar_content.customer_name == "John Doe"
        assert ar_content.status == ArContentStatus.ACTIVE
        assert ar_content.created_at is not None

    async def test_ar_content_computed_properties(self, test_session: AsyncSession, ar_content_factory):
        """Test computed properties return correct values"""
        ar_content = await ar_content_factory(test_session)
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        # Test public_link
        public_link = ar_content.public_link
        assert public_link == f"/ar/{ar_content.id}"
        
        # Test qr_code_path
        qr_path = ar_content.qr_code_path
        assert qr_path == f"/storage/qr/{ar_content.id}.png"

    async def test_ar_content_order_number_unique(self, test_session: AsyncSession, project_factory, ar_content_factory):
        """Test order_number is unique within project"""
        project = await project_factory(test_session)
        
        # Create first AR content
        content1 = await ar_content_factory(test_session, project_id=project.id, order_number="UNIQUE-001")
        await test_session.commit()
        
        # Try to create second with same order_number - should fail
        content2 = ARContent(
            project_id=project.id,
            order_number="UNIQUE-001",  # Same as content1
            customer_name="Another Customer"
        )
        test_session.add(content2)
        
        # Should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            await test_session.commit()

    async def test_ar_content_order_number_different_projects(self, test_session: AsyncSession, project_factory, ar_content_factory):
        """Test same order_number can exist in different projects"""
        project1 = await project_factory(test_session)
        project2 = await project_factory(test_session)
        
        # Create AR content with same order_number in different projects
        content1 = await ar_content_factory(test_session, project_id=project1.id, order_number="SAME-001")
        content2 = await ar_content_factory(test_session, project_id=project2.id, order_number="SAME-001")
        
        await test_session.commit()
        
        # Both should exist successfully
        assert content1.order_number == "SAME-001"
        assert content2.order_number == "SAME-001"
        assert content1.project_id != content2.project_id

    async def test_ar_content_relationship_project(self, test_session: AsyncSession, ar_content_factory, project_factory):
        """Test ar_content.project relationship works"""
        project = await project_factory(test_session, name="Parent Project")
        ar_content = await ar_content_factory(test_session, project_id=project.id, order_number="PROJ-001")
        
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.project.id == project.id
        assert ar_content.project.name == "Parent Project"

    async def test_ar_content_relationship_videos(self, test_session: AsyncSession, ar_content_factory, video_factory):
        """Test ar_content.videos relationship works"""
        ar_content = await ar_content_factory(test_session)
        
        # Create multiple videos
        video1 = await video_factory(test_session, ar_content_id=ar_content.id, filename="video1.mp4")
        video2 = await video_factory(test_session, ar_content_id=ar_content.id, filename="video2.mp4")
        
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert len(ar_content.videos) == 2
        filenames = [video.filename for video in ar_content.videos]
        assert "video1.mp4" in filenames
        assert "video2.mp4" in filenames

    async def test_ar_content_active_video_none(self, test_session: AsyncSession, ar_content_factory):
        """Test active_video returns None when no active video set"""
        ar_content = await ar_content_factory(test_session)
        await test_session.commit()
        
        assert ar_content.active_video is None

    async def test_ar_content_active_video_set(self, test_session: AsyncSession, ar_content_factory, video_factory):
        """Test active_video relationship works when set"""
        ar_content = await ar_content_factory(test_session)
        video = await video_factory(test_session, ar_content_id=ar_content.id)
        
        # Set as active video
        ar_content.active_video_id = video.id
        
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.active_video is not None
        assert ar_content.active_video.id == video.id
        assert ar_content.active_video.filename == video.filename

    async def test_ar_content_company_id_property(self, test_session: AsyncSession, ar_content_factory, project_factory, company_factory):
        """Test company_id property returns project's company_id"""
        company = await company_factory(test_session)
        project = await project_factory(test_session, company_id=company.id)
        ar_content = await ar_content_factory(test_session, project_id=project.id)
        
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.company_id == company.id

    async def test_ar_content_repr(self, test_session: AsyncSession, ar_content_factory):
        """Test __repr__ method works correctly"""
        ar_content = await ar_content_factory(test_session, order_number="TEST-REPR")
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        repr_str = repr(ar_content)
        assert "ARContent" in repr_str
        assert f"id={ar_content.id}" in repr_str
        assert "order_number=TEST-REPR" in repr_str
        assert f"status={ar_content.status}" in repr_str


@pytest.mark.asyncio
class TestVideo:
    """Test cases for Video model"""

    async def test_video_create(self, test_session: AsyncSession, video_factory, ar_content_factory):
        """Test creating a video"""
        ar_content = await ar_content_factory(test_session)
        video = await video_factory(
            test_session,
            ar_content_id=ar_content.id,
            filename="test_video.mp4",
            video_status=VideoStatus.READY
        )
        
        await test_session.commit()
        await test_session.refresh(video)
        
        assert video.id is not None
        assert video.ar_content_id == ar_content.id
        assert video.filename == "test_video.mp4"
        assert video.video_status == VideoStatus.READY
        assert video.created_at is not None

    async def test_video_status_default(self, test_session: AsyncSession, ar_content_factory):
        """Test video gets default status"""
        ar_content = await ar_content_factory(test_session)
        video = Video(ar_content_id=ar_content.id, filename="default_status.mp4")
        
        test_session.add(video)
        await test_session.commit()
        await test_session.refresh(video)
        
        assert video.video_status == VideoStatus.UPLOADED

    async def test_video_relationship_ar_content(self, test_session: AsyncSession, video_factory, ar_content_factory):
        """Test video.ar_content relationship works"""
        ar_content = await ar_content_factory(test_session, order_number="VIDEO-TEST")
        video = await video_factory(test_session, ar_content_id=ar_content.id, filename="relationship_test.mp4")
        
        await test_session.commit()
        await test_session.refresh(video)
        
        assert video.ar_content.id == ar_content.id
        assert video.ar_content.order_number == "VIDEO-TEST"

    async def test_video_with_metadata(self, test_session: AsyncSession, video_factory, ar_content_factory):
        """Test creating video with metadata"""
        ar_content = await ar_content_factory(test_session)
        video = await video_factory(test_session, ar_content_id=ar_content.id)
        
        # Add metadata
        video.duration = 120  # 2 minutes
        video.size = 1024000  # 1MB
        
        await test_session.commit()
        await test_session.refresh(video)
        
        assert video.duration == 120
        assert video.size == 1024000


@pytest.mark.asyncio
class TestCascadeDelete:
    """Test cascade delete functionality"""

    async def test_cascade_delete_project_deletes_content(self, test_session: AsyncSession, company_factory, project_factory, ar_content_factory, video_factory):
        """Test deleting project deletes its AR content and videos"""
        company = await company_factory(test_session)
        project = await project_factory(test_session, company_id=company.id)
        
        # Create AR content with videos
        ar_content = await ar_content_factory(test_session, project_id=project.id)
        video = await video_factory(test_session, ar_content_id=ar_content.id)
        
        await test_session.commit()
        
        # Verify everything exists
        assert await test_session.get(Project, project.id) is not None
        assert await test_session.get(ARContent, ar_content.id) is not None
        assert await test_session.get(Video, video.id) is not None
        
        # Delete the project
        await test_session.delete(project)
        await test_session.commit()
        
        # Verify cascade delete worked
        assert await test_session.get(Project, project.id) is None
        assert await test_session.get(ARContent, ar_content.id) is None
        assert await test_session.get(Video, video.id) is None

    async def test_cascade_delete_company_deletes_projects_and_content(self, test_session: AsyncSession, company_factory, project_factory, ar_content_factory):
        """Test deleting company deletes its projects and AR content"""
        company = await company_factory(test_session)
        project = await project_factory(test_session, company_id=company.id)
        ar_content = await ar_content_factory(test_session, project_id=project.id)
        
        await test_session.commit()
        
        # Verify everything exists
        assert await test_session.get(Company, company.id) is not None
        assert await test_session.get(Project, project.id) is not None
        assert await test_session.get(ARContent, ar_content.id) is not None
        
        # Delete the company
        await test_session.delete(company)
        await test_session.commit()
        
        # Verify cascade delete worked
        assert await test_session.get(Company, company.id) is None
        assert await test_session.get(Project, project.id) is None
        assert await test_session.get(ARContent, ar_content.id) is None

    async def test_cascade_delete_ar_content_deletes_videos(self, test_session: AsyncSession, project_factory, ar_content_factory, video_factory):
        """Test deleting AR content deletes its videos"""
        project = await project_factory(test_session)
        ar_content = await ar_content_factory(test_session, project_id=project.id)
        video1 = await video_factory(test_session, ar_content_id=ar_content.id)
        video2 = await video_factory(test_session, ar_content_id=ar_content.id)
        
        await test_session.commit()
        
        # Verify everything exists
        assert await test_session.get(ARContent, ar_content.id) is not None
        assert await test_session.get(Video, video1.id) is not None
        assert await test_session.get(Video, video2.id) is not None
        
        # Delete AR content
        await test_session.delete(ar_content)
        await test_session.commit()
        
        # Verify cascade delete worked
        assert await test_session.get(ARContent, ar_content.id) is None
        assert await test_session.get(Video, video1.id) is None
        assert await test_session.get(Video, video2.id) is None


@pytest.mark.asyncio
class TestRelationshipQueries:
    """Test that relationships work correctly with queries"""

    async def test_query_company_with_projects(self, test_session: AsyncSession, company_factory, project_factory):
        """Test querying company and accessing projects relationship"""
        company = await company_factory(test_session, name="Query Test Company")
        
        # Create projects
        for i in range(3):
            await project_factory(test_session, company_id=company.id, name=f"Project {i+1}")
        
        await test_session.commit()
        
        # Query company and check projects
        result = await test_session.execute(
            select(Company).where(Company.name == "Query Test Company")
        )
        queried_company = result.scalar_one()
        
        assert len(queried_company.projects) == 3
        project_names = [p.name for p in queried_company.projects]
        assert "Project 1" in project_names
        assert "Project 2" in project_names
        assert "Project 3" in project_names

    async def test_query_project_with_content_and_videos(self, test_session: AsyncSession, project_factory, ar_content_factory, video_factory):
        """Test querying project and accessing nested relationships"""
        project = await project_factory(test_session, name="Nested Test Project")
        
        # Create AR content with videos
        for i in range(2):
            ar_content = await ar_content_factory(test_session, project_id=project.id, order_number=f"ORDER-{i+1:03d}")
            # Add videos to each content
            for j in range(2):
                await video_factory(test_session, ar_content_id=ar_content.id, filename=f"video_{i+1}_{j+1}.mp4")
        
        await test_session.commit()
        
        # Query project and check nested relationships
        result = await test_session.execute(
            select(Project).where(Project.name == "Nested Test Project")
        )
        queried_project = result.scalar_one()
        
        assert len(queried_project.ar_contents) == 2
        
        total_videos = 0
        for content in queried_project.ar_contents:
            total_videos += len(content.videos)
            
        assert total_videos == 4  # 2 content items × 2 videos each


@pytest.mark.asyncio
class TestDefaultStatuses:
    """Test that models have correct default statuses"""

    async def test_company_default_status(self, test_session: AsyncSession):
        """Test Company model has correct default status"""
        company = Company(name="Test Company")
        test_session.add(company)
        await test_session.commit()
        await test_session.refresh(company)
        
        assert company.status == CompanyStatus.ACTIVE

    async def test_project_default_status(self, test_session: AsyncSession, company_factory):
        """Test Project model has correct default status"""
        company = await company_factory(test_session)
        
        project = Project(name="Test Project", company_id=company.id)
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)
        
        assert project.status == ProjectStatus.ACTIVE

    async def test_ar_content_default_status(self, test_session: AsyncSession, project_factory):
        """Test ARContent model has correct default status"""
        project = await project_factory(test_session)
        
        ar_content = ARContent(
            project_id=project.id,
            order_number="TEST-001",
            customer_name="Test Customer"
        )
        test_session.add(ar_content)
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.status == ArContentStatus.PENDING

    async def test_video_default_status(self, test_session: AsyncSession, ar_content_factory):
        """Test Video model has correct default status"""
        ar_content = await ar_content_factory(test_session)
        
        video = Video(
            ar_content_id=ar_content.id,
            filename="test_video.mp4"
        )
        test_session.add(video)
        await test_session.commit()
        await test_session.refresh(video)
        
        assert video.video_status == VideoStatus.UPLOADED


@pytest.mark.asyncio
class TestComputedProperties:
    """Test computed properties work correctly"""

    async def test_company_computed_properties_empty(self, test_session: AsyncSession, company_factory):
        """Test Company computed properties with no projects/content"""
        company = await company_factory(test_session)
        await test_session.commit()
        
        assert company.projects_count == 0
        assert company.ar_content_count == 0

    async def test_company_computed_properties_with_data(self, test_session: AsyncSession, company_factory, project_factory, ar_content_factory):
        """Test Company computed properties with projects and content"""
        company = await company_factory(test_session)
        
        # Create 2 projects
        project1 = await project_factory(test_session, company_id=company.id)
        project2 = await project_factory(test_session, company_id=company.id)
        
        # Create AR content (3 in project1, 2 in project2)
        for i in range(3):
            await ar_content_factory(test_session, project_id=project1.id, order_number=f"PROJ1-{i+1:03d}")
        for i in range(2):
            await ar_content_factory(test_session, project_id=project2.id, order_number=f"PROJ2-{i+1:03d}")
        
        await test_session.commit()
        
        assert company.projects_count == 2
        assert company.ar_content_count == 5

    async def test_project_computed_properties_empty(self, test_session: AsyncSession, project_factory):
        """Test Project computed properties with no AR content"""
        project = await project_factory(test_session)
        await test_session.commit()
        
        assert project.ar_content_count == 0

    async def test_project_computed_properties_with_content(self, test_session: AsyncSession, project_factory, ar_content_factory):
        """Test Project computed properties with AR content"""
        project = await project_factory(test_session)
        
        # Create 4 AR content items
        for i in range(4):
            await ar_content_factory(test_session, project_id=project.id, order_number=f"CONTENT-{i+1:03d}")
        
        await test_session.commit()
        
        assert project.ar_content_count == 4

    async def test_ar_content_public_link_property(self, test_session: AsyncSession, ar_content_factory):
        """Test ARContent public_link property"""
        ar_content = await ar_content_factory(test_session)
        await test_session.commit()
        
        expected_link = f"/ar-content/{ar_content.unique_id}"
        assert ar_content.public_link == expected_link

    async def test_ar_content_company_id_property(self, test_session: AsyncSession, ar_content_factory):
        """Test ARContent company_id property"""
        ar_content = await ar_content_factory(test_session)
        await test_session.commit()
        await test_session.refresh(ar_content)
        
        assert ar_content.company_id == ar_content.project.company_id
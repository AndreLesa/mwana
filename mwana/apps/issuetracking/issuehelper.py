# vim: ai ts=4 sts=4 et sw=4

from mwana.apps.issuetracking.models import Issue
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class IssueHelper:   

    def get_issues(self, page=1):
        """
        Returns issues with pagination
        """
        
        issues = Issue.objects.all()
        
        if not page:
            page = 1
        
            
        paginator = Paginator(issues, 10)
        try:
            p_issues = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            p_issues = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            p_issues = paginator.page(paginator.num_pages)

        counter = p_issues.start_index()
        
        number=p_issues.number
        has_previous = p_issues.has_previous()
        has_next = p_issues.has_next()
        paginator_num_pages = p_issues.paginator.num_pages
        return p_issues.object_list, paginator_num_pages, number, has_next, has_previous
    